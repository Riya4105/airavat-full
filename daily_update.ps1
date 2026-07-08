# daily_update.ps1
# Run this every day to keep AIRAVAT data current

$env:DATABASE_URL = "postgresql://postgres.tttmvhybjozckwcnwont@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
$env:DB_PASSWORD = "riyajoshi4105#"

Write-Host "Starting daily AIRAVAT update..." -ForegroundColor Cyan

Write-Host "Step 1: Fetching satellite data..." -ForegroundColor Yellow
python ingestion\daily_ingest.py

Write-Host "Step 2: Recomputing baselines..." -ForegroundColor Yellow
python ingestion\compute_baselines.py

Write-Host "Done! Supabase database updated." -ForegroundColor Green
Write-Host "Run 'python esg_engine\vae_encoder.py' weekly and push models." -ForegroundColor Gray