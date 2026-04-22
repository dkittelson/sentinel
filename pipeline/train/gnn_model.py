"""GNN-LSTM model for conflict continuation prediction.

Architecture:
  1. Feature MLP: 80 features → 64-dim per hex per timestep
  2. GraphSAGE: 2 layers over H3 adjacency (captures 2-hop spatial diffusion)
  3. GRU: processes 14-day sequence of spatial embeddings
  4. Prediction head: 64 → 32 → 1

Designed to run on Kaggle T4 (15GB VRAM). ~120K parameters.
"""
import torch
import torch.nn as nn
import numpy as np

try:
    from torch_geometric.nn import SAGEConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False


class SpatialEncoder(nn.Module):
    """Simple neighbor pooling — works without torch_geometric."""

    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.self_linear = nn.Linear(in_dim, out_dim)
        self.neighbor_linear = nn.Linear(in_dim, out_dim)
        self.norm = nn.LayerNorm(out_dim)

    def forward(self, x, neighbor_map, hex_idx):
        """
        x: (num_hexes, in_dim) — per-hex features
        neighbor_map: dict {hex_id: [neighbor_hex_ids]}
        hex_idx: dict {hex_id: index}
        """
        self_out = self.self_linear(x)

        # Aggregate neighbor features (mean pooling)
        neighbor_out = torch.zeros_like(self_out)
        for hid, idx in hex_idx.items():
            neighbors = neighbor_map.get(hid, [])
            if neighbors:
                n_indices = [hex_idx[n] for n in neighbors if n in hex_idx]
                if n_indices:
                    neighbor_out[idx] = x[n_indices].mean(dim=0)

        combined = self_out + self.neighbor_linear(neighbor_out)
        return torch.relu(self.norm(combined))


class GNNLSTMModel(nn.Module):
    """GNN-LSTM for spatiotemporal conflict continuation prediction."""

    def __init__(self, n_features, hidden_dim=64, gru_layers=1, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim

        # Feature encoder
        self.feature_mlp = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Spatial encoder (2 layers for 2-hop diffusion)
        self.spatial1 = SpatialEncoder(hidden_dim, hidden_dim)
        self.spatial2 = SpatialEncoder(hidden_dim, hidden_dim)

        # Temporal encoder
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=gru_layers,
            batch_first=True,
            dropout=dropout if gru_layers > 1 else 0,
        )

        # Prediction head
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout * 1.5),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x_seq, neighbor_map=None, hex_idx=None):
        """
        x_seq: (batch_hexes, seq_len, n_features) — temporal sequences per hex
        neighbor_map: dict for spatial aggregation (optional)
        hex_idx: dict mapping hex_id to batch index (optional)

        Returns: (batch_hexes, 1) — predicted probabilities
        """
        batch_size, seq_len, n_features = x_seq.shape

        # Encode features at each timestep
        # Reshape: (batch * seq, features) → MLP → (batch * seq, hidden)
        x_flat = x_seq.reshape(-1, n_features)
        h_flat = self.feature_mlp(x_flat)
        h = h_flat.reshape(batch_size, seq_len, self.hidden_dim)

        # Spatial aggregation at each timestep (if graph provided)
        if neighbor_map is not None and hex_idx is not None:
            spatial_out = []
            for t in range(seq_len):
                h_t = h[:, t, :]  # (batch_hexes, hidden)
                h_t = self.spatial1(h_t, neighbor_map, hex_idx)
                h_t = self.spatial2(h_t, neighbor_map, hex_idx)
                spatial_out.append(h_t)
            h = torch.stack(spatial_out, dim=1)  # (batch, seq, hidden)

        # Temporal encoding
        gru_out, _ = self.gru(h)  # (batch, seq, hidden)
        final_hidden = gru_out[:, -1, :]  # last timestep

        # Prediction
        logits = self.head(final_hidden)
        return logits.squeeze(-1)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class PerHexGRU(nn.Module):
    """Simpler model — GRU only, no spatial component.

    Use this as the baseline to compare against GNN-LSTM.
    If this doesn't beat XGBoost, the GNN-LSTM won't either.
    """

    def __init__(self, n_features, hidden_dim=64, gru_layers=2, dropout=0.2):
        super().__init__()
        self.gru = nn.GRU(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=gru_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout * 1.5),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x_seq, **kwargs):
        """x_seq: (batch, seq_len, n_features) → (batch,) logits"""
        gru_out, _ = self.gru(x_seq)
        final = gru_out[:, -1, :]
        return self.head(final).squeeze(-1)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class FocalLoss(nn.Module):
    """Focal loss for class imbalance — same concept as XGBoost focal."""

    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits, targets):
        bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        probs = torch.sigmoid(logits)
        pt = torch.where(targets == 1, probs, 1 - probs)
        alpha_t = torch.where(targets == 1, self.alpha, 1 - self.alpha)
        focal_weight = alpha_t * (1 - pt) ** self.gamma
        return (focal_weight * bce).mean()
