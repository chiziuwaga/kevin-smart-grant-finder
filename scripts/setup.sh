#!/bin/bash

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1: $2"
}

# Check Python installation
if ! command -v python3 &> /dev/null; then
    log "ERROR" "Python not found. Please install Python 3.9 or later."
    exit 1
fi

# Check Git installation
if ! command -v git &> /dev/null; then
    log "ERROR" "Git not found. Please install Git."
    exit 1
fi

# Create and activate virtual environment
log "INFO" "Creating virtual environment..."
if [ -d "venv" ]; then
    log "INFO" "Removing existing virtual environment..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    log "ERROR" "Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
log "INFO" "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    log "ERROR" "Failed to activate virtual environment"
    exit 1
fi

# Install dependencies
log "INFO" "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    log "ERROR" "Failed to install dependencies"
    exit 1
fi

# Create necessary directories
directories=(
    "agents"
    "config"
    "dashboard"
    "database"
    "tests"
    "utils"
    "utils/grant_sources"
    "utils/api_handlers"
    "utils/scrapers"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        log "INFO" "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Copy .env.example if it doesn't exist
if [ ! -f ".env" ]; then
    log "INFO" "Creating .env from template..."
    cp .env.example .env
fi

# Verify installations
log "INFO" "Verifying installations..."
packages=(
    "streamlit"
    "pinecone-client"
    "pymongo"
    "requests"
    "beautifulsoup4"
)

for package in "${packages[@]}"; do
    python -c "import $package; print(f'$package version: {$package.__version__}')"
    if [ $? -ne 0 ]; then
        log "WARNING" "Failed to verify $package installation"
    fi
done

# Setup git hooks
log "INFO" "Setting up git hooks..."
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
# Run tests before commit
python -m pytest tests/
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
EOF

# Make hook executable
chmod +x .git/hooks/pre-commit

log "INFO" "Setup completed successfully!"
log "INFO" "Next steps:"
log "INFO" "1. Update .env with your API keys"
log "INFO" "2. Run 'streamlit run dashboard/app.py' to start the application"
log "INFO" "3. Run 'pytest tests/' to verify the test suite"