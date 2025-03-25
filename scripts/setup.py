import os
import sys
import subprocess
import venv
from pathlib import Path

def log(message, level="INFO"):
    print(f"[{level}] {message}")

def create_venv():
    log("Creating virtual environment...")
    venv_path = Path("venv")
    if venv_path.exists():
        log("Removing existing virtual environment...")
        import shutil
        shutil.rmtree(venv_path)
    
    venv.create("venv", with_pip=True)
    log("Virtual environment created successfully")

def install_dependencies():
    log("Installing dependencies...")
    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    result = subprocess.run(pip_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Failed to install dependencies: {result.stderr}", "ERROR")
        sys.exit(1)
    log("Dependencies installed successfully")

def create_project_structure():
    log("Creating project structure...")
    directories = [
        "agents",
        "config",
        "dashboard",
        "database",
        "tests",
        "utils",
        "utils/grant_sources",
        "utils/api_handlers",
        "utils/scrapers"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            log(f"Creating directory: {directory}")
            path.mkdir(parents=True, exist_ok=True)

def setup_env():
    if not Path(".env").exists() and Path(".env.example").exists():
        log("Creating .env from template...")
        import shutil
        shutil.copy(".env.example", ".env")

def main():
    log("Starting project setup...")
    
    try:
        create_venv()
        install_dependencies()
        create_project_structure()
        setup_env()
        
        log("Setup completed successfully!")
        log("Next steps:")
        log("1. Update .env with your API keys")
        log("2. Run 'streamlit run dashboard/app.py' to start the application")
        log("3. Run 'pytest tests/' to verify the test suite")
    
    except Exception as e:
        log(f"Setup failed: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()