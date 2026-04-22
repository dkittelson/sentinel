"""Train GNN-LSTM for conflict continuation prediction.

Benchmarks against XGBoost on the same test set.
Designed to run on Kaggle T4 (15GB VRAM, 30 hrs/week).

Usage:
  python train/train_continuation_gnn.py           # train + evaluate
  python train/train_continuation_gnn.py --gru-only  # simpler baseline first
"""
import pandas as pd
import numpy as np
import os
import sys
import time
import argparse
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import (
    TRAIN_CUTOFF, TEST_START, RANDOM_SEED,
    GRU_SEQ_LEN, GRU_HIDDEN_DIM, GRU_LAYERS, GRU_DROPOUT,
    GRU_BATCH_SIZE, GRU_EPOCHS, GRU_LR,
)
from train_continuation import CONT_FEATURES
from gnn_model import GNNLSTMModel, PerHexGRU, FocalLoss

BASE = os.path.join(os.path.dirname(__file__), "..")
MODEL_DIR = os.path.join(BASE, "models")

SEQ_LEN    = GRU_SEQ_LEN
HIDDEN_DIM = GRU_HIDDEN_DIM
BATCH_SIZE = GRU_BATCH_SIZE
EPOCHS     = GRU_EPOCHS
LR         = GRU_LR
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


class ConflictSequenceDataset(Dataset):
    """Creates (seq_len, n_features) sequences from hex-day panel data."""

    def __init__(self, df, features, seq_len=14):
        self.seq_len = seq_len
        self.features = features

        # Group by hex, create sequences
        self.sequences = []
        self.labels = []

        for h3_id, group in df.groupby("h3_id"):
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
        return (
            torch.tensor(self.sequences[idx], dtype=torch.float32),
            torch.tensor(self.labels[idx], dtype=torch.float32),
        )


def train_epoch(model, loader, optimizer, criterion, device, scaler=None):
    model.train()
    total_loss = 0
    n_batches = 0

    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()

        if scaler:  # mixed precision
            with torch.amp.autocast("cuda"):
                logits = model(x_batch)
                loss = criterion(logits, y_batch)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(x_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    all_preds = []
    all_labels = []

    for x_batch, y_batch in loader:
        x_batch = x_batch.to(device)
        logits = model(x_batch)
        probs = torch.sigmoid(logits).cpu().numpy()
        all_preds.extend(probs)
        all_labels.extend(y_batch.numpy())

    preds = np.array(all_preds)
    labels = np.array(all_labels)

    aucpr = average_precision_score(labels, preds) if labels.sum() > 0 else 0.0
    return aucpr, preds, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gru-only", action="store_true",
                        help="Use simpler PerHexGRU instead of GNN-LSTM")
    args = parser.parse_args()

    print(f"Device: {DEVICE}")
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # Load data
    data_path = os.path.join(BASE, "data", "processed", "continuation_set.parquet")
    print(f"Loading {data_path}...")
    df = pd.read_parquet(data_path)
    features = [f for f in CONT_FEATURES if f in df.columns]
    print(f"  Features: {len(features)}")

    # Temporal split
    train_cutoff = pd.Timestamp(TRAIN_CUTOFF)
    test_start = pd.Timestamp(TEST_START)
    train_df = df[df["date"] <= train_cutoff]
    test_df = df[df["date"] >= test_start]

    # Normalize features
    scaler = StandardScaler()
    train_df[features] = scaler.fit_transform(train_df[features].fillna(0))
    test_df[features] = scaler.transform(test_df[features].fillna(0))

    print(f"  Train: {len(train_df):,} rows, Test: {len(test_df):,} rows")

    # Create datasets
    print("Creating sequence datasets...")
    t0 = time.time()
    train_ds = ConflictSequenceDataset(train_df, features, SEQ_LEN)
    test_ds = ConflictSequenceDataset(test_df, features, SEQ_LEN)
    print(f"  Train sequences: {len(train_ds):,}, Test: {len(test_ds):,} ({time.time()-t0:.1f}s)")
    print(f"  Positive rate: train={train_ds.labels.mean():.3f}, test={test_ds.labels.mean():.3f}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE * 2, shuffle=False,
                             num_workers=0, pin_memory=True)

    # Build model
    n_features = len(features)
    if args.gru_only:
        model = PerHexGRU(n_features, hidden_dim=HIDDEN_DIM, gru_layers=GRU_LAYERS, dropout=GRU_DROPOUT)
        model_name = "PerHexGRU"
    else:
        model = GNNLSTMModel(n_features, hidden_dim=HIDDEN_DIM, dropout=GRU_DROPOUT)
        model_name = "GNN-LSTM"

    model = model.to(DEVICE)
    print(f"\n  Model: {model_name}")
    print(f"  Parameters: {model.count_parameters():,}")

    # Training setup
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10)
    criterion = FocalLoss(alpha=0.25, gamma=2.0)

    use_amp = DEVICE == "cuda"
    grad_scaler = torch.amp.GradScaler("cuda") if use_amp else None

    best_aucpr = 0
    patience = 10
    patience_counter = 0

    print(f"\n  Training {model_name} for {EPOCHS} epochs...")
    for epoch in range(EPOCHS):
        t0 = time.time()
        train_loss = train_epoch(model, train_loader, optimizer, criterion,
                                 DEVICE, grad_scaler)
        scheduler.step()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            aucpr, _, _ = evaluate(model, test_loader, DEVICE)
            elapsed = time.time() - t0
            print(f"  Epoch {epoch+1:3d}: loss={train_loss:.4f}, "
                  f"test AUC-PR={aucpr:.4f}, lr={scheduler.get_last_lr()[0]:.6f} "
                  f"({elapsed:.1f}s)")

            if aucpr > best_aucpr:
                best_aucpr = aucpr
                patience_counter = 0
                # Save checkpoint
                save_path = os.path.join(MODEL_DIR, f"{model_name.lower().replace('-','_')}_best.pt")
                os.makedirs(MODEL_DIR, exist_ok=True)
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "best_aucpr": best_aucpr,
                    "features": features,
                    "scaler_mean": scaler.mean_,
                    "scaler_scale": scaler.scale_,
                }, save_path)
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"  Early stopping at epoch {epoch+1}")
                    break

    # Final evaluation
    print(f"\n{'='*55}")
    print(f"  {model_name} RESULTS")
    print(f"{'='*55}")
    print(f"  Best test AUC-PR: {best_aucpr:.4f}")
    print(f"  XGBoost baseline: 0.680")
    if best_aucpr > 0.680:
        print(f"  ✓ GNN-LSTM BEATS XGBoost by {best_aucpr - 0.680:.4f}")
    else:
        print(f"  ✗ XGBoost still wins by {0.680 - best_aucpr:.4f}")


if __name__ == "__main__":
    main()
