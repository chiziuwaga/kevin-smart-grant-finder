# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from pathlib import Path

from pkg_resources import working_set


def check_python_version():
    """Check if Python version is 3.8 or higher"""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    if current_version < required_version:
        print(f"❌ Python {required_version[0]}.{required_version[1]} or higher is required")
        return False
    print(f"✅ Python version {sys.version.split()[0]} detected")
    return True

def check_venv():
    """Check if running in a virtual environment"""
    # Skip virtual environment check in CI environments (e.g., GitHub Actions)
    if os.getenv("CI", "false").lower() == "true":
        print("⚠️ Skipping virtual environment check in CI environment")
        return True
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print("❌ Not running in a virtual environment")
        return False
    print("✅ Virtual environment detected")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'streamlit': 'streamlit',
        'pinecone-client': 'pinecone_client',
        'pymongo': 'pymongo',
        'requests': 'requests',
        'beautifulsoup4': 'bs4'
    }
    
    installed_packages = {pkg.key: pkg.version for pkg in working_set}
    all_installed = True
    
    for package_name, import_name in required_packages.items():
        if package_name in installed_packages:
            print(f"✅ {package_name} is installed (version {installed_packages[package_name]})")
        else:
            print(f"❌ {package_name} is not installed")
            all_installed = False
    
    return all_installed

def check_project_structure():
    """Check if required project directories exist"""
    required_dirs = [
        'agents',
        'config',
        'dashboard',
        'database',
        'tests',
        'utils'
    ]
    
    all_exist = True
    for directory in required_dirs:
        if not Path(directory).is_dir():
            print(f"❌ {directory}/ directory is missing")
            all_exist = False
        else:
            print(f"✅ {directory}/ directory exists")
    return all_exist

def check_mongodb_connection():
    """Check if MongoDB is reachable using the MongoDBClient class."""
    try:
        from database.mongodb_client import MongoDBClient
        client = MongoDBClient()
        # ping the server to verify
        client.client.admin.command('ping')
        print("✅ MongoDB ping successful")
        return True
    except Exception as e:
        print(f"❌ MongoDB connectivity check failed: {e}")
        return False

def main():
    """Main verification function"""
    print("\n🔍 Verifying project setup...\n")
    
    checks = [
        ("Python Version", check_python_version()),
        ("Virtual Environment", check_venv()),
        ("Dependencies", check_dependencies()),
        ("Project Structure", check_project_structure()),
        ("MongoDB Connection", check_mongodb_connection())
    ]
    
    print("\n📋 Summary:")
    all_passed = all(result for _, result in checks)
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    if all_passed:
        print("\n✨ All checks passed! The project is properly set up.")
        return 0
    else:
        print("\n⚠️ Some checks failed. Please address the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
