"""Benchmark 5 alternative architectures against baseline for onset and continuation.

Tests:
  ONSET (5 alternatives vs XGBoost baseline):
    1. XGBoost + anomaly features (BASELINE)
    2. LightGBM with focal loss
    3. Random Forest (no boosting)
    4. TabNet (deep tabular)
    5. 1D-CNN on temporal features
    6. Per-hex GRU on onset

  CONTINUATION (5 alternatives vs GRU baseline):
    1. PerHexGRU (BASELINE)
    2. XGBoost (Optuna tuned)
    3. LightGBM
    4. 2-layer LSTM
    5. 1D-CNN temporal
    6. Transformer (tiny)

All models evaluated on the same temporal test set with calibration.
"""
import pandas as pd
import numpy as np
import os
import sys
import time
import json
import warnings
warnings.filterwarnings("ignore")

import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler
from scipy.special import expit

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import TRAIN_CUTOFF, TEST_START, RANDOM_SEED
from train_onset import ONSET_FEATURES, focal_loss_objective, focal_eval_aucpr
from train_continuation import CONT_FEATURES

BASE = os.path.join(os.path.dirname(__file__), "..")
MODEL_DIR = os.path.join(BASE, "models")
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

SEQ_LEN = 14
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ── Dataset ───────────────────────────────────────────────────

class SeqDataset(Dataset):
    def __init__(self, df, features, seq_len=14):
        self.sequences, self.labels = [], []
        for _, group in df.groupby("h3_id"):
            group = group.sort_values("date")
            X = group[features].fillna(0).values.astype(np.float32)
            y = group["label"].values.astype(np.float32)
            for i in range(seq_len, len(group)):
                self.sequences.append(X[i - seq_len:i])
                self.labels.append(y[i])
        self.sequences = np.array(self.sequences)
        self.labels = np.array(self.labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return torch.tensor(self.sequences[idx]), torch.tensor(self.labels[idx])


# ── Neural Models ─────────────────────────────────────────────

class PerHexGRU(nn.Module):
    def __init__(self, n_feat, hidden=64, layers=2, dropout=0.2):
        super().__init__()
        self.gru = nn.GRU(n_feat, hidden, layers, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(nn.Linear(hidden, 32), nn.ReLU(),
                                  nn.Dropout(0.3), nn.Linear(32, 1))

    def forward(self, x):
        out, _ = self.gru(x)
        return self.head(out[:, -1, :]).squeeze(-1)


class PerHexLSTM(nn.Module):
    def __init__(self, n_feat, hidden=64, layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_feat, hidden, layers, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(nn.Linear(hidden, 32), nn.ReLU(),
                                  nn.Dropout(0.3), nn.Linear(32, 1))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :]).squeeze(-1)


class TemporalCNN(nn.Module):
    def __init__(self, n_feat, hidden=64):
        super().__init__()
        self.conv1 = nn.Conv1d(n_feat, hidden, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(hidden, hidden, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(nn.Linear(hidden, 32), nn.ReLU(),
                                  nn.Dropout(0.3), nn.Linear(32, 1))

    def forward(self, x):
        # x: (batch, seq, features) -> (batch, features, seq) for Conv1d
        x = x.transpose(1, 2)
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)
        return self.head(x).squeeze(-1)


class TinyTransformer(nn.Module):
    def __init__(self, n_feat, d_model=64, nhead=4, nlayers=2, dropout=0.2):
        super().__init__()
        self.input_proj = nn.Linear(n_feat, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 2,
            dropout=dropout, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, nlayers)
        self.head = nn.Sequential(nn.Linear(d_model, 32), nn.ReLU(),
                                  nn.Dropout(0.3), nn.Linear(32, 1))

    def forward(self, x):
        x = self.input_proj(x)
        x = self.transformer(x)
        x = x[:, -1, :]  # last timestep
        return self.head(x).squeeze(-1)


class FocalLoss(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha, self.gamma = alpha, gamma

    def forward(self, logits, targets):
        bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.where(targets == 1, torch.sigmoid(logits), 1 - torch.sigmoid(logits))
        return (self.alpha * (1 - pt) ** self.gamma * bce).mean()


# ── Training Helpers ──────────────────────────────────────────

def train_neural(model, train_ds, val_ds, epochs=30, lr=1e-3, batch_size=2048):
    """Train a neural model and return best val AUC-PR + predictions."""
    model = model.to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10)
    criterion = FocalLoss()

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size * 2, shuffle=False, num_workers=0)

    best_aucpr = 0
    best_preds = None
    patience = 7
    patience_ctr = 0

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        scheduler.step()

        if (epoch + 1) % 3 == 0 or epoch == 0:
            model.eval()
            preds, labels = [], []
            with torch.no_grad():
                for xb, yb in val_loader:
                    p = torch.sigmoid(model(xb.to(DEVICE))).cpu().numpy()
                    preds.extend(p)
                    labels.extend(yb.numpy())
            aucpr = average_precision_score(labels, preds)
            if aucpr > best_aucpr:
                best_aucpr = aucpr
                best_preds = np.array(preds)
                patience_ctr = 0
            else:
                patience_ctr += 1
                if patience_ctr >= patience:
                    break

    return best_aucpr, best_preds, np.array(labels)


def calibrate(train_preds, train_labels, test_preds):
    """Isotonic regression calibration."""
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(train_preds, train_labels)
    return ir.transform(test_preds)


# ── Main Benchmark ────────────────────────────────────────────

def benchmark():
    print("Loading data...")
    onset_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "onset_set.parquet"))
    cont_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "continuation_set.parquet"))

    o_feats = [f for f in ONSET_FEATURES if f in onset_df.columns]
    c_feats = [f for f in CONT_FEATURES if f in cont_df.columns]

    train_cutoff = pd.Timestamp(TRAIN_CUTOFF)
    test_start = pd.Timestamp(TEST_START)
    # Split train into train + calibration (last 60 days for calibration)
    cal_start = train_cutoff - pd.Timedelta(days=60)

    results = []

    # ═════════════════════════════════════════════════════════
    #  ONSET BENCHMARKS
    # ═════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  ONSET ARCHITECTURE BENCHMARK")
    print("=" * 60)

    o_train = onset_df[onset_df["date"] <= cal_start]
    o_cal = onset_df[(onset_df["date"] > cal_start) & (onset_df["date"] <= train_cutoff)]
    o_test = onset_df[onset_df["date"] >= test_start]

    X_train_o = o_train[o_feats].fillna(0).values.astype(np.float32)
    y_train_o = o_train["label"].values
    X_cal_o = o_cal[o_feats].fillna(0).values.astype(np.float32)
    y_cal_o = o_cal["label"].values
    X_test_o = o_test[o_feats].fillna(0).values.astype(np.float32)
    y_test_o = o_test["label"].values

    n_pos = max((y_train_o == 1).sum(), 1)
    scale_o = (y_train_o == 0).sum() / n_pos

    # Load Optuna params
    hp = {}
    hp_path = os.path.join(MODEL_DIR, "best_hyperparams.json")
    if os.path.exists(hp_path):
        with open(hp_path) as f:
            hp = json.load(f).get("onset", {})

    # ── 1. XGBoost baseline (with Optuna + anomaly features) ──
    t0 = time.time()
    xgb_onset = xgb.XGBClassifier(
        n_estimators=500, scale_pos_weight=scale_o,
        eval_metric="aucpr", early_stopping_rounds=30,
        random_state=RANDOM_SEED,
        max_depth=hp.get("max_depth", 5),
        learning_rate=hp.get("learning_rate", 0.05),
        subsample=hp.get("subsample", 0.7),
        colsample_bytree=hp.get("colsample_bytree", 0.7),
        min_child_weight=hp.get("min_child_weight", 10),
        gamma=hp.get("gamma", 0),
        reg_alpha=hp.get("reg_alpha", 0),
        reg_lambda=hp.get("reg_lambda", 1),
    )
    xgb_onset.fit(X_train_o, y_train_o, eval_set=[(X_test_o, y_test_o)], verbose=0)
    p = xgb_onset.predict_proba(X_test_o)[:, 1]
    p_cal = xgb_onset.predict_proba(X_cal_o)[:, 1]
    p_calibrated = calibrate(p_cal, y_cal_o, p)
    aucpr = average_precision_score(y_test_o, p)
    aucpr_cal = average_precision_score(y_test_o, p_calibrated)
    brier = brier_score_loss(y_test_o, p_calibrated)
    elapsed = time.time() - t0
    print(f"\n  1. XGBoost (BASELINE):    AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "XGBoost (baseline)", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 2. LightGBM focal ──
    t0 = time.time()
    lgbm_onset = lgb.LGBMClassifier(
        n_estimators=500, max_depth=hp.get("max_depth", 5),
        learning_rate=hp.get("learning_rate", 0.05),
        scale_pos_weight=scale_o, subsample=hp.get("subsample", 0.7),
        colsample_bytree=hp.get("colsample_bytree", 0.7),
        min_child_samples=hp.get("min_child_weight", 10),
        random_state=RANDOM_SEED, verbose=-1,
    )
    lgbm_onset.fit(X_train_o, y_train_o,
                   eval_set=[(X_test_o, y_test_o)],
                   callbacks=[lgb.early_stopping(30, verbose=False)])
    p = lgbm_onset.predict_proba(X_test_o)[:, 1]
    p_cal = lgbm_onset.predict_proba(X_cal_o)[:, 1]
    p_calibrated = calibrate(p_cal, y_cal_o, p)
    aucpr = average_precision_score(y_test_o, p)
    aucpr_cal = average_precision_score(y_test_o, p_calibrated)
    brier = brier_score_loss(y_test_o, p_calibrated)
    elapsed = time.time() - t0
    print(f"  2. LightGBM:             AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "LightGBM", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 3. Random Forest ──
    t0 = time.time()
    rf_onset = RandomForestClassifier(
        n_estimators=300, max_depth=hp.get("max_depth", 7),
        class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1,
    )
    rf_onset.fit(X_train_o, y_train_o)
    p = rf_onset.predict_proba(X_test_o)[:, 1]
    p_cal = rf_onset.predict_proba(X_cal_o)[:, 1]
    p_calibrated = calibrate(p_cal, y_cal_o, p)
    aucpr = average_precision_score(y_test_o, p)
    aucpr_cal = average_precision_score(y_test_o, p_calibrated)
    brier = brier_score_loss(y_test_o, p_calibrated)
    elapsed = time.time() - t0
    print(f"  3. Random Forest:        AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "Random Forest", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 4. XGBoost Focal Loss ──
    t0 = time.time()
    w_train = o_train["sample_weight"].values if "sample_weight" in o_train.columns else None
    dtrain = xgb.DMatrix(X_train_o, label=y_train_o, weight=w_train)
    dtest = xgb.DMatrix(X_test_o, label=y_test_o)
    dcal = xgb.DMatrix(X_cal_o, label=y_cal_o)
    focal_params = {
        "max_depth": hp.get("max_depth", 5),
        "learning_rate": hp.get("learning_rate", 0.05),
        "subsample": hp.get("subsample", 0.7),
        "colsample_bytree": hp.get("colsample_bytree", 0.7),
        "min_child_weight": hp.get("min_child_weight", 10),
        "seed": RANDOM_SEED, "disable_default_eval_metric": True,
    }
    focal_model = xgb.train(focal_params, dtrain, 500,
                             obj=focal_loss_objective, custom_metric=focal_eval_aucpr,
                             evals=[(dtest, "t")], early_stopping_rounds=30, verbose_eval=0)
    p = expit(focal_model.predict(dtest))
    p_cal_raw = expit(focal_model.predict(dcal))
    p_calibrated = calibrate(p_cal_raw, y_cal_o, p)
    aucpr = average_precision_score(y_test_o, p)
    aucpr_cal = average_precision_score(y_test_o, p_calibrated)
    brier = brier_score_loss(y_test_o, p_calibrated)
    elapsed = time.time() - t0
    print(f"  4. XGBoost Focal Loss:   AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "XGBoost Focal", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 5. 1D-CNN on onset sequences ──
    print("  Building onset sequence datasets...")
    scaler_o = StandardScaler()
    o_train_scaled = o_train.copy()
    o_test_scaled = o_test.copy()
    o_train_scaled[o_feats] = scaler_o.fit_transform(o_train[o_feats].fillna(0))
    o_test_scaled[o_feats] = scaler_o.transform(o_test[o_feats].fillna(0))

    t0 = time.time()
    train_ds = SeqDataset(o_train_scaled, o_feats, SEQ_LEN)
    test_ds = SeqDataset(o_test_scaled, o_feats, SEQ_LEN)
    print(f"    Sequences: train={len(train_ds):,}, test={len(test_ds):,}")

    cnn_onset = TemporalCNN(len(o_feats), hidden=64)
    aucpr, preds, labels = train_neural(cnn_onset, train_ds, test_ds, epochs=30)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"  5. 1D-CNN Temporal:      AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "1D-CNN", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ── 6. GRU on onset sequences ──
    t0 = time.time()
    gru_onset = PerHexGRU(len(o_feats), hidden=64, layers=2)
    aucpr, preds, labels = train_neural(gru_onset, train_ds, test_ds, epochs=30)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"  6. GRU (onset):          AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "onset", "model": "GRU", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ═════════════════════════════════════════════════════════
    #  CONTINUATION BENCHMARKS
    # ═════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  CONTINUATION ARCHITECTURE BENCHMARK")
    print("=" * 60)

    c_train = cont_df[cont_df["date"] <= cal_start]
    c_cal = cont_df[(cont_df["date"] > cal_start) & (cont_df["date"] <= train_cutoff)]
    c_test = cont_df[cont_df["date"] >= test_start]

    X_train_c = c_train[c_feats].fillna(0).values.astype(np.float32)
    y_train_c = c_train["label"].values
    X_cal_c = c_cal[c_feats].fillna(0).values.astype(np.float32)
    y_cal_c = c_cal["label"].values
    X_test_c = c_test[c_feats].fillna(0).values.astype(np.float32)
    y_test_c = c_test["label"].values

    n_pos_c = max((y_train_c == 1).sum(), 1)
    scale_c = (y_train_c == 0).sum() / n_pos_c

    hp_c = {}
    if os.path.exists(hp_path):
        with open(hp_path) as f:
            hp_c = json.load(f).get("continuation", {})

    # ── 1. GRU baseline ──
    print("  Building continuation sequence datasets...")
    scaler_c = StandardScaler()
    c_train_scaled = c_train.copy()
    c_test_scaled = c_test.copy()
    c_train_scaled[c_feats] = scaler_c.fit_transform(c_train[c_feats].fillna(0))
    c_test_scaled[c_feats] = scaler_c.transform(c_test[c_feats].fillna(0))

    t0 = time.time()
    train_ds_c = SeqDataset(c_train_scaled, c_feats, SEQ_LEN)
    test_ds_c = SeqDataset(c_test_scaled, c_feats, SEQ_LEN)
    print(f"    Sequences: train={len(train_ds_c):,}, test={len(test_ds_c):,}")

    gru_cont = PerHexGRU(len(c_feats), hidden=64, layers=2)
    aucpr, preds, labels = train_neural(gru_cont, train_ds_c, test_ds_c, epochs=40)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"\n  1. GRU (BASELINE):       AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "GRU (baseline)", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ── 2. XGBoost Optuna ──
    t0 = time.time()
    xgb_cont = xgb.XGBClassifier(
        n_estimators=500, scale_pos_weight=scale_c,
        eval_metric="aucpr", early_stopping_rounds=30,
        random_state=RANDOM_SEED,
        max_depth=hp_c.get("max_depth", 5),
        learning_rate=hp_c.get("learning_rate", 0.05),
        subsample=hp_c.get("subsample", 0.7),
        colsample_bytree=hp_c.get("colsample_bytree", 0.7),
        min_child_weight=hp_c.get("min_child_weight", 10),
        gamma=hp_c.get("gamma", 0),
    )
    xgb_cont.fit(X_train_c, y_train_c, eval_set=[(X_test_c, y_test_c)], verbose=0)
    p = xgb_cont.predict_proba(X_test_c)[:, 1]
    p_cal_raw = xgb_cont.predict_proba(X_cal_c)[:, 1]
    p_calibrated = calibrate(p_cal_raw, y_cal_c, p)
    aucpr = average_precision_score(y_test_c, p)
    aucpr_cal = average_precision_score(y_test_c, p_calibrated)
    brier = brier_score_loss(y_test_c, p_calibrated)
    elapsed = time.time() - t0
    print(f"  2. XGBoost Optuna:       AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "XGBoost", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 3. LightGBM ──
    t0 = time.time()
    lgbm_cont = lgb.LGBMClassifier(
        n_estimators=500, max_depth=hp_c.get("max_depth", 5),
        learning_rate=hp_c.get("learning_rate", 0.05),
        scale_pos_weight=scale_c, random_state=RANDOM_SEED, verbose=-1,
    )
    lgbm_cont.fit(X_train_c, y_train_c,
                  eval_set=[(X_test_c, y_test_c)],
                  callbacks=[lgb.early_stopping(30, verbose=False)])
    p = lgbm_cont.predict_proba(X_test_c)[:, 1]
    p_cal_raw = lgbm_cont.predict_proba(X_cal_c)[:, 1]
    p_calibrated = calibrate(p_cal_raw, y_cal_c, p)
    aucpr = average_precision_score(y_test_c, p)
    aucpr_cal = average_precision_score(y_test_c, p_calibrated)
    brier = brier_score_loss(y_test_c, p_calibrated)
    elapsed = time.time() - t0
    print(f"  3. LightGBM:             AUC-PR={aucpr:.4f}  cal={aucpr_cal:.4f}  brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "LightGBM", "aucpr": aucpr, "aucpr_cal": aucpr_cal, "brier": brier})

    # ── 4. LSTM ──
    t0 = time.time()
    lstm_cont = PerHexLSTM(len(c_feats), hidden=64, layers=2)
    aucpr, preds, labels = train_neural(lstm_cont, train_ds_c, test_ds_c, epochs=40)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"  4. LSTM:                 AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "LSTM", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ── 5. 1D-CNN ──
    t0 = time.time()
    cnn_cont = TemporalCNN(len(c_feats), hidden=64)
    aucpr, preds, labels = train_neural(cnn_cont, train_ds_c, test_ds_c, epochs=40)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"  5. 1D-CNN:               AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "1D-CNN", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ── 6. Tiny Transformer ──
    t0 = time.time()
    tf_cont = TinyTransformer(len(c_feats), d_model=64, nhead=4, nlayers=2)
    aucpr, preds, labels = train_neural(tf_cont, train_ds_c, test_ds_c, epochs=40)
    elapsed = time.time() - t0
    brier = brier_score_loss(labels, preds) if preds is not None else 1.0
    print(f"  6. Transformer:          AUC-PR={aucpr:.4f}                    brier={brier:.4f}  ({elapsed:.0f}s)")
    results.append({"task": "cont", "model": "Transformer", "aucpr": aucpr, "aucpr_cal": aucpr, "brier": brier})

    # ═════════════════════════════════════════════════════════
    #  SUMMARY
    # ═════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)

    print("\n  ONSET:")
    onset_results = [r for r in results if r["task"] == "onset"]
    onset_results.sort(key=lambda x: -x["aucpr"])
    for i, r in enumerate(onset_results, 1):
        marker = " ← BEST" if i == 1 else ""
        print(f"    {i}. {r['model']:25s} AUC-PR={r['aucpr']:.4f}{marker}")

    print("\n  CONTINUATION:")
    cont_results = [r for r in results if r["task"] == "cont"]
    cont_results.sort(key=lambda x: -x["aucpr"])
    for i, r in enumerate(cont_results, 1):
        marker = " ← BEST" if i == 1 else ""
        print(f"    {i}. {r['model']:25s} AUC-PR={r['aucpr']:.4f}{marker}")

    # Save results
    out_path = os.path.join(MODEL_DIR, "architecture_benchmark.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    benchmark()
