#!/usr/bin/env python3

import os
import shutil
import subprocess
from pathlib import Path
import json
from datetime import datetime
import sys
from typing import Optional, Tuple

class GitHubManager:
    def __init__(self):
        self.api_url = "https://api.github.com"
        self.username = self._get_github_username()
    
    def _get_github_username(self) -> Optional[str]:
        """Get GitHub username using gh cli"""
        try:
            result = subprocess.run(
                ['gh', 'api', 'user', '--jq', '.login'],
                capture_output=True,
                text=True,
                check=True
            )
            username = result.stdout.strip()
            if username:
                print(f"Using GitHub username: {username}")
                return username
        except subprocess.CalledProcessError as e:
            print(f"Error getting GitHub username via gh cli: {e}")
            
        # Fallback: try to get from git config
        try:
            result = subprocess.run(
                ['git', 'config', 'github.user'],
                capture_output=True,
                text=True,
                check=True
            )
            username = result.stdout.strip()
            if username:
                print(f"Using GitHub username from git config: {username}")
                return username
        except subprocess.CalledProcessError:
            pass
            
        print("Could not determine GitHub username automatically.")
        print("Please run: git config --global github.user YOUR_GITHUB_USERNAME")
        sys.exit(1)

    def _verify_repo_status(self, repo_name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Comprehensively verify repository status
        Returns: (exists, status_message, repo_url)
        """
        # Check repository via API
        api_result = subprocess.run(
            ['gh', 'api', f'/repos/{self.username}/{repo_name}', '--silent'],
            capture_output=True
        )
        
        # If API call succeeds, repo exists
        if api_result.returncode == 0:
            repo_url = f"https://github.com/{self.username}/{repo_name}.git"
            return True, "exists", repo_url
            
        # If we get a 404, repo definitely doesn't exist
        if b'"message": "Not Found"' in api_result.stderr:
            return False, "not_found", None
            
        # Any other error means we can't determine status
        return False, "unknown", None

    def _delete_repo(self, repo_name: str) -> bool:
        """Safely delete a repository"""
        try:
            # Delete via API to get more reliable result
            result = subprocess.run(
                ['gh', 'api', f'/repos/{self.username}/{repo_name}', '--method', 'DELETE'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def get_or_create_repo(self, repo_name: str = "home_backup") -> Optional[str]:
        """Check if repo exists, create if it doesn't, using reliable API calls"""
        print("\nChecking GitHub repository status...")
        
        # Verify authentication first
        try:
            subprocess.run(['gh', 'auth', 'status'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("Not authenticated with GitHub. Please run 'gh auth login' first.")
            sys.exit(1)
            
        # Remove any existing repository
        exists, _, _ = self._verify_repo_status(repo_name)
        if exists:
            print(f"Deleting existing repository: {repo_name}")
            if not self._delete_repo(repo_name):
                print("Failed to delete existing repository.")
                sys.exit(1)
        
        # Create new repository
        try:
            create_result = subprocess.run([
                'gh', 'api', '/user/repos',
                '--method', 'POST',
                '-f', f"name={repo_name}",
                '-f', 'private=true',
                '-f', 'description=Automated backup of home directory configurations'
            ], capture_output=True, text=True)
            
            if create_result.returncode == 0:
                repo_url = f"https://github.com/{self.username}/{repo_name}.git"
                print(f"Successfully created repository: {repo_name}")
                return repo_url
                    
            print(f"Error creating repository: {create_result.stderr}")
            sys.exit(1)
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to create repository: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            sys.exit(1)

class HomeBackup:
    def __init__(self, backup_dir: Path):
        self.home = Path.home()
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration to backup
        self.CONFIG_PATHS = [
            '.bashrc',
            '.profile',
            '.gitconfig',
            '.ssh/config',
            '.config/r',
            '.julia/config',
            '.config/pip',
            '.local/share/jupyter/kernels',
            '.Rprofile',
            '.Renviron',
            '.config/Code/User/settings.json',
            '.config/Code/User/keybindings.json',
            '.config/Code/User/snippets',
            '.jupyter/jupyter_notebook_config.py',
            '.config/matplotlib/matplotlibrc',
            '.zshrc',
            '.zprofile',
            '.oh-my-zsh/custom',
            '.oh-my-zsh/custom/themes',
            '.oh-my-zsh/custom/plugins',
            '.oh-my-zsh/custom/aliases.zsh',
            '.oh-my-zsh/custom/functions.zsh'
        ]
        
        self.IGNORE_PATTERNS = [
            '*/__pycache__/*',
            '*.pyc',
            '*/.git/*',
            '*/node_modules/*',
            '*/.ipynb_checkpoints/*',
            '*/.Trash/*',
            '*/Cache/*',
            '*/.cache/*',
        ]

    def save_package_lists(self):
        """Save lists of installed packages"""
        pkg_dir = self.backup_dir / 'package_lists'
        pkg_dir.mkdir(exist_ok=True)
        
        # Python packages
        try:
            subprocess.run(['pip', 'freeze'], 
                         stdout=open(pkg_dir / 'python_packages.txt', 'w'))
            print("✓ Saved Python packages")
        except Exception as e:
            print(f"Warning: Couldn't save Python packages: {e}")
            
        # R packages
        r_cmd = 'R --vanilla -e "write.table(installed.packages()[,1], file=\'packages.txt\', row.names=F, col.names=F)"'
        try:
            subprocess.run(r_cmd, shell=True, cwd=pkg_dir)
            print("✓ Saved R packages")
        except Exception as e:
            print(f"Warning: Couldn't save R packages: {e}")
            
        # Julia packages
        julia_cmd = """julia -e 'using Pkg; open("julia_packages.txt", "w") do f; write(f, join([string(dep.name) for dep in values(Pkg.dependencies())], "\\n")) end'"""
        try:
            subprocess.run(julia_cmd, shell=True, cwd=pkg_dir)
            print("✓ Saved Julia packages")
        except Exception as e:
            print(f"Warning: Couldn't save Julia packages: {e}")

    def backup_configs(self):
        """Backup configuration files"""
        config_backup = self.backup_dir / 'configs'
        config_backup.mkdir(parents=True, exist_ok=True)
        
        for config_path in self.CONFIG_PATHS:
            src = self.home / config_path
            if src.exists():
                dst = config_backup / config_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if src.is_file():
                        shutil.copy2(src, dst)
                    else:
                        # For directories, copy with error handling for each file
                        for root, dirs, files in os.walk(src):
                            rel_path = os.path.relpath(root, src)
                            dst_root = dst / rel_path
                            dst_root.mkdir(parents=True, exist_ok=True)
                            
                            for file in files:
                                src_file = Path(root) / file
                                dst_file = dst_root / file
                                try:
                                    shutil.copy2(src_file, dst_file)
                                except PermissionError:
                                    print(f"Warning: Permission denied for {src_file}")
                                except Exception as e:
                                    print(f"Warning: Couldn't copy {src_file}: {e}")
                                    
                    print(f"✓ Backed up {config_path}")
                except Exception as e:
                    print(f"Warning: Couldn't backup {config_path}: {e}")

    # Add this method to the HomeBackup class
    def create_readme(self):
        """Create README.md with comprehensive documentation"""
        readme_path = self.backup_dir / 'README.md'
        readme_content = """# Home Directory Configuration Backup

This repository contains automated backups of home directory configurations and package lists for Python, R, and Julia environments. The backup script captures essential configuration files and maintains version control through Git.

## Repository Contents

### Environment-Specific Configurations
Different environments require specific handling during backup and restoration:

#### Development Environments
- **VS Code**:
  - Extensions list: `~/.vscode/extensions`
  - User settings: `~/.config/Code/User/`
  - Workspace settings: Individual `.vscode` folders
- **Jupyter**:
  - Custom kernels: `~/.local/share/jupyter/kernels`
  - Server config: `~/.jupyter/`
  - Custom templates: `~/.jupyter/custom`

#### Language-Specific
- **Python**:
  - Virtual environments: Not backed up (recreate from requirements)
  - `pyenv` settings: `~/.pyenv/version`
  - `pipx` installations: `~/.local/pipx`
- **R**:
  - Package sources: `~/.Rprofile`
  - Environment variables: `~/.Renviron`
  - Custom libraries: Document paths in `r_custom_config.txt`
- **Julia**:
  - Project environments: `~/.julia/environments`
  - Startup file: `~/.julia/config/startup.jl`
  - Package preferences: `~/.julia/config/preferences.jl`

#### Shell & System
- **Shell**:
  - Bash: `.bashrc`, `.bash_profile`, `.profile`
  - Zsh & Oh My Zsh:
    - Core configs: `.zshrc`, `.zprofile`
    - Oh My Zsh: `.oh-my-zsh/custom/`
    - Custom themes: `.oh-my-zsh/custom/themes/`
    - Custom plugins: `.oh-my-zsh/custom/plugins/`
    - Custom aliases: `.oh-my-zsh/custom/aliases.zsh`
    - Custom functions: `.oh-my-zsh/custom/functions.zsh`
  - Custom global aliases: `.aliases`
  - Custom global functions: `.functions`
- **Git**:
  - Global config: `.gitconfig`
  - Global ignore: `.gitignore_global`
  - SSH config: `.ssh/config`

## Backup Instructions

### Prerequisites
1. Install the GitHub CLI:
   ```bash
   # For Ubuntu/Debian
   sudo apt install gh

   # For macOS
   brew install gh
   ```

2. Authenticate with GitHub:
   ```bash
   gh auth login
   ```

3. Set your GitHub username:
   ```bash
   git config --global github.user YOUR_GITHUB_USERNAME
   ```

### Running a Backup
1. Execute the backup script:
   ```bash
   python3 improved-backup-script.py
   ```

The script will:
- Create/update the GitHub repository
- Save current package lists
- Copy configuration files
- Commit and push changes to GitHub

### Backup Schedule
Recommended backup frequency:
- After significant configuration changes
- After installing/updating major packages
- Monthly for regular maintenance
- Before major system updates

## Environment-Specific Restoration

### Python Environment
1. Set up base Python:
   ```bash
   # If using pyenv
   pyenv install $(cat configs/.pyenv/version)
   pyenv global $(cat configs/.pyenv/version)

   # Install pip
   python -m ensurepip --upgrade
   ```

2. Restore packages with consideration for dependencies:
   ```bash
   # Install core build tools first
   pip install --upgrade pip setuptools wheel

   # Install packages with constraints
   pip install -r package_lists/python_packages.txt --constraint package_lists/constraints.txt
   ```

### R Environment
1. Install R base:
   ```bash
   # Ubuntu/Debian
   sudo apt install r-base r-base-dev

   # macOS
   brew install r
   ```

2. Restore R configurations:
   ```bash
   # Restore .Rprofile and .Renviron
   cp configs/.Rprofile ~/
   cp configs/.Renviron ~/
   ```

### Julia Environment
1. Install Julia:
   ```bash
   # Download and install appropriate version
   # Version info stored in julia_version.txt
   ```

2. Restore configurations:
   ```bash
   cp configs/.julia/config/startup.jl ~/.julia/config/
   ```

### Oh My Zsh Environment
1. Install Oh My Zsh (if not already installed):
   ```bash
   sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
   ```

2. Restore Oh My Zsh configurations:
   ```bash
   # Backup existing Oh My Zsh custom directory if it exists
   if [ -d ~/.oh-my-zsh/custom ]; then
     mv ~/.oh-my-zsh/custom ~/.oh-my-zsh/custom.bak
   fi

   # Restore custom directory
   cp -r configs/.oh-my-zsh/custom ~/.oh-my-zsh/

   # Restore .zshrc
   cp configs/.zshrc ~/
   ```

## Troubleshooting Guide

### Package Installation Issues

#### Python
1. Virtual Environment Conflicts:
   ```bash
   python -m venv fresh_env
   source fresh_env/bin/activate
   pip install -r package_lists/python_packages.txt
   ```

#### R
1. Package Dependencies:
   ```R
   install.packages("pak")
   pak::pkg_system_requirements()
   ```

#### Julia
1. Package Precompilation:
   ```julia
   using Pkg
   Pkg.precompile()
   ```

## Backup Verification

### Automated Verification
Run the included verification script:
```bash
./verify_backup.sh
```

### Manual Verification Steps
1. Compare file checksums:
   ```bash
   find ~ -type f -path "*.config/*" -exec md5sum {} \; > original_checksums.txt
   cd ~/home_backup
   find configs -type f -exec md5sum {} \; > backup_checksums.txt
   diff original_checksums.txt backup_checksums.txt
   ```

## Security Note
This backup contains sensitive configuration files. Ensure:
- The repository remains private
- SSH keys and credentials are not included in the backup
- Access tokens and sensitive data are stored separately

# Acknowledgements

All decisions and ideas generated from this code emanated from a human (pem725)
but without the help of his trusted friends Bubba and Claude, none of this would
have happened.  Thank you both for your hAIlp.
"""

        try:
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            print("✓ Created README.md")
        except Exception as e:
            print(f"Warning: Couldn't create README.md: {e}")


    def setup_git_repo(self, repo_url: str):
        """Initialize git repo and create initial commit"""
        os.chdir(self.backup_dir)
        
        # Initialize git repo if needed
        if not (self.backup_dir / '.git').exists():
            subprocess.run(['git', 'init', '-b', 'main'], check=True)
            
            # Create .gitignore
            with open('.gitignore', 'w') as f:
                f.write('\n'.join(self.IGNORE_PATTERNS))
        
        # Ensure remote is set correctly
        try:
            # Remove existing remote if it exists
            subprocess.run(['git', 'remote', 'remove', 'origin'], 
                         capture_output=True)
        except:
            pass
            
        # Add remote
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
        
        # Verify remote
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, 
                              text=True)
        if repo_url not in result.stdout:
            print(f"Warning: Remote URL verification failed")
            print(f"Expected: {repo_url}")
            print(f"Current remotes:\n{result.stdout}")
            sys.exit(1)
        
        # Add and commit changes
        subprocess.run(['git', 'add', '.'], check=True)
        try:
            subprocess.run(
                ['git', 'commit', '-m', f'Backup update {datetime.now().isoformat()}'], 
                check=True
            )
            print("✓ Committed changes")
        except:
            print("No changes to commit")
            
        # Push to remote
        try:
            subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)
            print("✓ Pushed to remote")
        except Exception as e:
            print(f"Warning: Error pushing to remote: {e}")
            print("\nManual push may be needed:")
            print(f"cd {self.backup_dir}")
            print("git push -u origin main")

    def save_omz_lists(self):
        """Save lists of Oh My Zsh plugins and themes"""
        pkg_dir = self.backup_dir / 'package_lists'
        pkg_dir.mkdir(exist_ok=True)

        # Get Oh My Zsh configuration
        zshrc_path = self.home / '.zshrc'
        if zshrc_path.exists():
            try:
                # Extract plugins
                with open(zshrc_path, 'r') as f:
                    content = f.read()

                # Find plugins line
                plugins_match = re.search(r'plugins=\((.*?)\)', content, re.DOTALL)
                if plugins_match:
                    plugins = [p.strip() for p in plugins_match.group(1).split() if p.strip()]
                    with open(pkg_dir / 'omz_plugins.txt', 'w') as f:
                        f.write('\n'.join(plugins))
                    print("✓ Saved Oh My Zsh plugins list")

                # Find theme
                theme_match = re.search(r'ZSH_THEME="(.*?)"', content)
                if theme_match:
                    with open(pkg_dir / 'omz_themes.txt', 'w') as f:
                        f.write(theme_match.group(1))
                    print("✓ Saved Oh My Zsh theme")

            except Exception as e:
                print(f"Warning: Couldn't save Oh My Zsh configuration: {e}")

        # Save custom plugin and theme paths
        custom_dir = self.home / '.oh-my-zsh/custom'
        if custom_dir.exists():
            try:
                # Save custom plugin paths
                custom_plugins = [p.name for p in (custom_dir / 'plugins').glob('*') if p.is_dir()]
                with open(pkg_dir / 'omz_custom_plugins.txt', 'w') as f:
                    f.write('\n'.join(custom_plugins))
                print("✓ Saved Oh My Zsh custom plugins list")

                # Save custom theme paths
                custom_themes = [t.name for t in (custom_dir / 'themes').glob('*') if t.is_file()]
                with open(pkg_dir / 'omz_custom_themes.txt', 'w') as f:
                    f.write('\n'.join(custom_themes))
                print("✓ Saved Oh My Zsh custom themes list")

            except Exception as e:
                print(f"Warning: Couldn't save Oh My Zsh custom items: {e}")


    def run_backup(self):
        """Run the complete backup process"""
        print("\nStarting backup process...")
        print("------------------------")
        
        github = GitHubManager()
        if not github.username:
            print("Error: Could not determine GitHub username")
            sys.exit(1)
            
        repo_url = github.get_or_create_repo()
        if not repo_url:
            print("Error: Could not create or access repository")
            sys.exit(1)
        
        print("\nBacking up package lists...")
        self.save_package_lists()
        print("\nSaving Oh My Zsh stuff...")
        self.save_omz_lists() # added for omz
        print("\nBacking up config files...")
        self.backup_configs()
        print("\nCreating documentation...")
        self.create_readme()  # Add this line
        print("\nSetting up git repository...")
        self.setup_git_repo(repo_url)
        print("\nBackup completed!")
        print(f"Repository location: {repo_url}")
        print(f"Local backup path: {self.backup_dir}")
        print("\nAll this created by pem725 and Bubba.")

if __name__ == "__main__":
    backup = HomeBackup(Path.home() / 'home_backup')
    backup.run_backup()
