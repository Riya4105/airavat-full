# daily_update.ps1
# Run this every day to keep AIRAVAT data current

$env:DATABASE_URL = "postgresql://postgres:MXBLoPGUarnkiDeWQHcCwgYyKNoLaqJW@roundhouse.proxy.rlwy.net:34947/railway"

Write-Host "Starting daily AIRAVAT update..." -ForegroundColor Cyan

venv\Scripts\activate

Write-Host "Step 1: Fetching satellite data..." -ForegroundColor Yellow
python ingestion\daily_ingest.py

Write-Host "Step 2: Recomputing baselines..." -ForegroundColor Yellow
python ingestion\compute_baselines.py

Write-Host "Done! Railway database updated." -ForegroundColor Green
Write-Host "Run 'python esg_engine\vae_encoder.py' weekly and push models." -ForegroundColor Gray