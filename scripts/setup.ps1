# PowerShell setup script for Kevin's Smart Grant Finder

Write-Host "[INFO] Starting project setup..."

# Create virtual environment
Write-Host "[INFO] Creating virtual environment..."
if (Test-Path venv) {
    Write-Host "[INFO] Removing existing virtual environment..."
    Remove-Item -Recurse -Force venv
}

python -m venv venv
if (-not $?) {
    Write-Host "[ERROR] Failed to create virtual environment"
    exit 1
}

# Activate virtual environment
Write-Host "[INFO] Activating virtual environment..."
.\venv\Scripts\Activate
if (-not $?) {
    Write-Host "[ERROR] Failed to activate virtual environment"
    exit 1
}

# Install dependencies
Write-Host "[INFO] Installing dependencies..."
pip install -r requirements.txt
if (-not $?) {
    Write-Host "[ERROR] Failed to install dependencies"
    exit 1
}

# Create project structure
Write-Host "[INFO] Creating project structure..."
$directories = @(
    "agents",
    "config",
    "dashboard",
    "database",
    "tests",
    "utils",
    "utils/grant_sources",
    "utils/api_handlers",
    "utils/scrapers"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "[INFO] Creating directory: $dir"
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "[INFO] Setup completed successfully!"
Write-Host "[INFO] Next steps:"
Write-Host "1. Update .env with your API keys"
Write-Host "2. Run 'streamlit run dashboard/app.py' to start the application"
Write-Host "3. Run 'pytest tests/' to verify the test suite"