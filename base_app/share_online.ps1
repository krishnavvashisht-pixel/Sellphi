# Run this script whenever you want to generate a public HTTPS link for phones and external users
Write-Host "Starting Cloudflare Public HTTPS Tunnel for Sellphi on port 8000..." -ForegroundColor Cyan
Write-Host "Ensure uvicorn is running (uvicorn app.main:app --port 8000)`n" -ForegroundColor Yellow

.\cloudflared.exe tunnel --url http://127.0.0.1:8000
