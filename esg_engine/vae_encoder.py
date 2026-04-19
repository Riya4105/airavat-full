# esg_engine/vae_encoder.py
# Variational Autoencoder for zone personality encoding
# Learns latent representation of each zone from 90-day history
# Replaces rolling mean/std baseline with richer latent vector

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import psycopg2
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from config.zones import ZONES

# ── Database ───────────────────────────────────────────────
def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname, port=parsed.port,
            database=parsed.path[1:], user=parsed.username,
            password=parsed.password, sslmode="require"
        )
    else:
        return psycopg2.connect(
            host="localhost", port=5432,
            database="airavat", user="airavat", password="airavat123"
        )

# ── VAE Architecture ───────────────────────────────────────
class ZoneVAE(nn.Module):
    """
    Variational Autoencoder for zone observation sequences.
    Input:  sequence of [SST, Chl-a] pairs (window_size x 2)
    Latent: 8-dimensional zone personality vector
    Output: reconstructed sequence
    """
    def __init__(self, input_dim=2, window_size=14, latent_dim=8):
        super().__init__()
        self.input_dim   = input_dim
        self.window_size = window_size
        self.latent_dim  = latent_dim
        flat = input_dim * window_size

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(flat, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        self.fc_mu      = nn.Linear(32, latent_dim)
        self.fc_log_var = nn.Linear(32, latent_dim)

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, flat)
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_log_var(h)

    def reparameterise(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterise(mu, log_var)
        return self.decoder(z), mu, log_var

    def get_latent(self, x):
        """Returns the latent vector (no sampling) for a given input."""
        with torch.no_grad():
            mu, _ = self.encode(x)
        return mu

# ── Data loading ───────────────────────────────────────────
def load_zone_data(zone_id: str, days: int = 90):
    """
    Loads SST + Chl-a history for a zone from the database.
    Returns numpy array of shape (N, 2).
    """
    conn = get_db()
    cur = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute("""
        SELECT sst, chl_a FROM zone_observations
        WHERE zone_id = %s AND time >= %s
          AND sst IS NOT NULL AND chl_a IS NOT NULL
        ORDER BY time ASC;
    """, (zone_id, cutoff))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return np.array(rows, dtype=np.float32)

def make_windows(data: np.ndarray, window_size: int = 14):
    """Converts a time series into overlapping windows."""
    windows = []
    for i in range(len(data) - window_size + 1):
        windows.append(data[i:i + window_size])
    return np.array(windows)

def normalise(data: np.ndarray):
    """Normalise each column to mean 0 std 1."""
    mean = data.mean(axis=0)
    std  = data.std(axis=0) + 1e-8
    return (data - mean) / std, mean, std

# ── Training ───────────────────────────────────────────────
def train_vae(zone_id: str, epochs: int = 100, window_size: int = 14):
    """
    Trains a VAE on the zone's historical data.
    Returns trained model and normalisation parameters.
    """
    print(f"  Loading data for {zone_id}...")
    raw = load_zone_data(zone_id)

    if len(raw) < window_size + 5:
        print(f"  Insufficient data ({len(raw)} rows) — skipping")
        return None, None, None

    norm, mean, std = normalise(raw)
    windows = make_windows(norm, window_size)

    X = torch.tensor(windows.reshape(len(windows), -1), dtype=torch.float32)
    dataset = TensorDataset(X)
    loader  = DataLoader(dataset, batch_size=16, shuffle=True)

    model = ZoneVAE(input_dim=2, window_size=window_size, latent_dim=8)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)

    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for (batch,) in loader:
            optim.zero_grad()
            recon, mu, log_var = model(batch)
            # Reconstruction loss + KL divergence
            recon_loss = nn.functional.mse_loss(recon, batch, reduction="sum")
            kl_loss    = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
            loss = recon_loss + 0.01 * kl_loss
            loss.backward()
            optim.step()
            total_loss += loss.item()

        if (epoch + 1) % 25 == 0:
            print(f"  Epoch {epoch+1}/{epochs} — loss: {total_loss:.2f}")

    return model, mean, std

# ── Anomaly scoring ────────────────────────────────────────
def compute_anomaly_score(model, mean, std, recent_obs: np.ndarray, window_size: int = 14):
    """
    Computes reconstruction error for recent observations.
    High error = observation is anomalous relative to learned zone personality.
    Returns score 0-1 (1 = highly anomalous).
    """
    if model is None or len(recent_obs) < window_size:
        return 0.0

    # Normalise using training stats
    norm = (recent_obs - mean) / (std + 1e-8)
    window = norm[-window_size:].flatten()
    x = torch.tensor(window, dtype=torch.float32).unsqueeze(0)

    model.eval()
    with torch.no_grad():
        recon, mu, _ = model(x)
        error = nn.functional.mse_loss(recon, x).item()

    # Convert error to 0-1 score
    score = 1.0 - 1.0 / (1.0 + error)
    return round(float(score), 4)

# ── Save / Load model ──────────────────────────────────────
def save_model(model, mean, std, zone_id: str, path: str = "data/models"):
    os.makedirs(path, exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "mean": mean,
        "std": std,
        "zone_id": zone_id
    }, f"{path}/vae_{zone_id}.pt")
    print(f"  Model saved: {path}/vae_{zone_id}.pt")

def load_model(zone_id: str, path: str = "data/models", window_size: int = 14):
    fpath = f"{path}/vae_{zone_id}.pt"
    if not os.path.exists(fpath):
        return None, None, None
    checkpoint = torch.load(fpath, weights_only=True)
    model = ZoneVAE(input_dim=2, window_size=window_size, latent_dim=8)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["mean"], checkpoint["std"]

# ── Train all zones ────────────────────────────────────────
def train_all_zones(epochs: int = 100, window_size: int = 14):
    print("=" * 55)
    print("AIRAVAT 3.0 — VAE Zone Encoder Training")
    print("=" * 55)

    results = {}
    for zone_id in ZONES.keys():
        zone_name = ZONES[zone_id]["name"]
        print(f"\nTraining {zone_id} — {zone_name}")
        model, mean, std = train_vae(zone_id, epochs=epochs, window_size=window_size)
        if model is not None:
            save_model(model, mean, std, zone_id)
            results[zone_id] = "trained"
        else:
            results[zone_id] = "skipped"

    print(f"\n{'=' * 55}")
    print("Training complete:")
    for zone_id, status in results.items():
        print(f"  {zone_id} {ZONES[zone_id]['name']:<22} {status}")
    print(f"{'=' * 55}")
    return results

if __name__ == "__main__":
    train_all_zones(epochs=150)