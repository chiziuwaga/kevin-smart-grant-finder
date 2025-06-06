# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create the standard directory structure if it doesn't exist"""
    directories = [
        'agents',
        'config',
        'dashboard',
        'database',
        'tests',
        'utils',
        'api',
        'agents',
        'templates',
        'docs'
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        init_file = dir_path / '__init__.py'
        init_file.touch()

def organize_files():
    """Move files to their appropriate directories"""
    moves = {
        # Agents
        'research_agent.py': 'agents/',
        'analysis_agent.py': 'agents/',
        
        # Database
        'mongodb_client.py': 'database/',
        'pinecone_client.py': 'database/',
        'models.py': 'database/',
        
        # Utils
        'helpers.py': 'utils/',
        'run_grant_search.py': 'utils/',
        
        # Tests
        'test_utils.py': 'tests/',
        'test_agents.py': 'tests/',
        
        # API
        'routes.py': 'api/',
        'api_handlers/*': 'api/',
        
        # Config
        'settings.py': 'config/',
        '.env.example': 'config/',
        
        # Templates
        'templates/*': 'templates/',
        'pages/*': 'templates/pages/',
        
        # Scrapers
        'scrapers/*': 'scrapers/',
        'grant_sources/*': 'scrapers/sources/',
        
        # Documentation
        'DEPLOYMENT.md': 'docs/',
        'List Of Links.md': 'docs/references.md',
        'README.md': '.',  # Keep in root
    }
    
    for source, dest in moves.items():
        try:
            if '*' in source:
                # Handle directory moves
                source_dir = source.replace('*', '')
                if os.path.exists(source_dir):
                    dest_dir = Path(dest)
                    dest_dir.mkdir(exist_ok=True)
                    for item in os.listdir(source_dir):
                        src_path = Path(source_dir) / item
                        dst_path = Path(dest) / item
                        if dst_path.exists():
                            if dst_path.is_file():
                                dst_path.unlink()
                            else:
                                shutil.rmtree(dst_path)
                        shutil.move(str(src_path), str(dst_path))
                    if Path(source_dir).exists():
                        shutil.rmtree(source_dir)
            else:
                # Handle file moves
                src_path = Path(source)
                if src_path.exists():
                    dst_path = Path(dest) / src_path.name
                    if dst_path.exists():
                        dst_path.unlink()
                    dst_path.parent.mkdir(exist_ok=True)
                    shutil.move(str(src_path), str(dst_path))
        except Exception as e:
            print(f"Error moving {source} to {dest}: {str(e)}")

def cleanup_unnecessary_files():
    """Remove unnecessary files and empty directories"""
    to_remove = [
        'Building Kevin\'s Smart Grant Finder Syst.py',  # This should be properly integrated
    ]
    
    for file in to_remove:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Error removing {file}: {str(e)}")

def main():
    """Main organization function"""
    print("🔧 Organizing project structure...")
    
    # Create directory structure
    create_directory_structure()
    print("✅ Created directory structure")
    
    # Organize files
    organize_files()
    print("✅ Organized files")
    
    # Cleanup unnecessary files
    cleanup_unnecessary_files()
    print("✅ Cleaned up unnecessary files")
    
    print("\n✨ Project organization complete!")

if __name__ == "__main__":
    main() 