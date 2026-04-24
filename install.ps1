# Food AI One-Click Installer & Launcher
Write-Host "🍲 Initializing Food AI Setup..." -ForegroundColor Cyan

# 1. Install/Update the package
Write-Host "📦 Installing food-ai from PyPI..." -ForegroundColor Yellow
pip install --upgrade food-ai

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Installation failed. Please check your internet connection or Python environment." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ Installation Successful!" -ForegroundColor Green

# 2. Automatically launch the dashboard
Write-Host "🌐 Launching your Personal Food Agent Dashboard..." -ForegroundColor Cyan
food-ai-launch
