import os
import sys
import subprocess
import venv
from pathlib import Path

def log(message, level="INFO"):
    print(f"[{level}] {message}")

def verify_python():
    log("Verifying Python installation...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        log("Python 3.9 or later is required", "ERROR")
        return False
    log(f"Python {version.major}.{version.minor}.{version.micro} found")
    return True

def verify_venv():
    log("Verifying virtual environment...")
    venv_path = Path("venv")
    if not venv_path.exists():
        log("Creating virtual environment...")
        venv.create("venv", with_pip=True)
        return True
    
    # Check if venv is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        log("Virtual environment exists but is not activated", "WARNING")
        return False
    
    log("Virtual environment is properly set up")
    return True

def verify_dependencies():
    log("Verifying dependencies...")
    required_packages = [
        "streamlit",
        "pinecone-client",
        "pymongo",
        "requests",
        "beautifulsoup4",
        "pytest",
        "python-dotenv"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        log(f"Installing missing packages: {', '.join(missing_packages)}")
        pip_cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
        result = subprocess.run(pip_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"Failed to install dependencies: {result.stderr}", "ERROR")
            return False
    
    log("All required packages are installed")
    return True

def verify_project_structure():
    log("Verifying project structure...")
    required_dirs = [
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
    
    missing_dirs = []
    for directory in required_dirs:
        path = Path(directory)
        if not path.exists():
            missing_dirs.append(directory)
            log(f"Creating missing directory: {directory}")
            path.mkdir(parents=True, exist_ok=True)
    
    if missing_dirs:
        log(f"Created missing directories: {', '.join(missing_dirs)}")
    else:
        log("All required directories exist")
    return True

def verify_env_file():
    log("Verifying environment file...")
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            log("Creating .env from template...")
            import shutil
            shutil.copy(env_example_path, env_path)
            log("Created .env file from template")
        else:
            log("No .env or .env.example file found", "WARNING")
            return False
    
    log("Environment file exists")
    return True

def verify_git_setup():
    log("Verifying Git setup...")
    git_dir = Path(".git")
    if not git_dir.exists():
        log("Initializing Git repository...")
        subprocess.run(["git", "init"], capture_output=True)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            with open(gitignore_path, "w") as f:
                f.write("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env
.venv
env/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""")
    
    log("Git repository is set up")
    return True

def main():
    log("Starting setup verification...")
    
    checks = [
        ("Python", verify_python),
        ("Virtual Environment", verify_venv),
        ("Dependencies", verify_dependencies),
        ("Project Structure", verify_project_structure),
        ("Environment File", verify_env_file),
        ("Git Setup", verify_git_setup)
    ]
    
    failed_checks = []
    for check_name, check_func in checks:
        log(f"\nVerifying {check_name}...")
        try:
            if not check_func():
                failed_checks.append(check_name)
        except Exception as e:
            log(f"Error during {check_name} verification: {str(e)}", "ERROR")
            failed_checks.append(check_name)
    
    if failed_checks:
        log("\nSetup verification completed with issues:", "WARNING")
        for check in failed_checks:
            log(f"- {check} check failed", "WARNING")
        sys.exit(1)
    else:
        log("\nSetup verification completed successfully!")
        log("\nNext steps:")
        log("1. Update .env with your API keys")
        log("2. Run 'streamlit run dashboard/app.py' to start the application")
        log("3. Run 'pytest tests/' to verify the test suite")

if __name__ == "__main__":
    main()