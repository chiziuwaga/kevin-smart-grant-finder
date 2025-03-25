# PowerShell setup script for Kevin's Smart Grant Finder

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to log messages
function Write-Log($message, $type = "INFO") {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $type: $message"
}

# Check Python installation
if (-not (Test-Command python)) {
    Write-Log "Python not found. Please install Python 3.9 or later." "ERROR"
    exit 1
}

# Check Git installation
if (-not (Test-Command git)) {
    Write-Log "Git not found. Please install Git." "ERROR"
    exit 1
}

# Create and activate virtual environment
Write-Log "Creating virtual environment..."
if (Test-Path venv) {
    Write-Log "Removing existing virtual environment..."
    Remove-Item -Recurse -Force venv
}

python -m venv venv
if (-not $?) {
    Write-Log "Failed to create virtual environment" "ERROR"
    exit 1
}

# Activate virtual environment
Write-Log "Activating virtual environment..."
.\venv\Scripts\Activate
if (-not $?) {
    Write-Log "Failed to activate virtual environment" "ERROR"
    exit 1
}

# Install dependencies
Write-Log "Installing dependencies..."
pip install -r requirements.txt
if (-not $?) {
    Write-Log "Failed to install dependencies" "ERROR"
    exit 1
}

# Create necessary directories
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
        Write-Log "Creating directory: $dir"
        New-Item -ItemType Directory -Path $dir -Force
    }
}

# Copy .env.example if it doesn't exist
if (-not (Test-Path .env)) {
    Write-Log "Creating .env from template..."
    Copy-Item .env.example .env
}

# Verify installations
Write-Log "Verifying installations..."
$packages = @(
    "streamlit",
    "pinecone-client",
    "pymongo",
    "requests",
    "beautifulsoup4"
)

foreach ($package in $packages) {
    python -c "import $package; print(f'$package version: {$package.__version__}')"
    if (-not $?) {
        Write-Log "Failed to verify $package installation" "WARNING"
    }
}

# Setup git hooks
Write-Log "Setting up git hooks..."
$preCommitHook = ".git/hooks/pre-commit"
@"
#!/bin/sh
# Run tests before commit
python -m pytest tests/
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
"@ | Out-File -FilePath $preCommitHook -Encoding UTF8

# Make hook executable
if (Test-Path $preCommitHook) {
    icacls $preCommitHook /grant Everyone:F
}

Write-Log "Setup completed successfully!"
Write-Log "Next steps:"
Write-Log "1. Update .env with your API keys"
Write-Log "2. Run 'streamlit run dashboard/app.py' to start the application"
Write-Log "3. Run 'pytest tests/' to verify the test suite"