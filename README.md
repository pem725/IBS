# IBS (Improved Backup Script)

A robust Python-based solution for backing up your development environment configurations to GitHub. This tool automatically captures and version controls your essential settings across multiple development tools and languages.

## 🎯 What It Does

IBS helps you:
- Backup configuration files for Python, R, Julia, and shell environments
- Track installed packages across different programming languages
- Version control your VS Code, Jupyter, and shell configurations
- Maintain Oh My Zsh customizations
- Automate GitHub repository management for your backups

## 🔧 What It Backs Up

### Development Environments
- VS Code settings, keybindings, and snippets
- Jupyter notebook configurations and custom kernels
- Git global configurations
- SSH configs

### Language-Specific Settings
- Python: pip packages list
- R: Installed packages, .Rprofile, .Renviron
- Julia: Package lists and configurations

### Shell Configurations
- Bash: .bashrc, .profile
- Zsh & Oh My Zsh: 
  - Core configurations
  - Custom themes and plugins
  - Custom aliases and functions

## 📋 Prerequisites

1. Python 3.6+
2. GitHub CLI (`gh`)
3. Git
4. Access to GitHub account
5. Installed development tools you want to backup (R, Julia, Python, etc.)

## 🚀 Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/IBS.git
   cd IBS
   ```

2. Install GitHub CLI and authenticate:
   ```bash
   # Ubuntu/Debian
   sudo apt install gh
   # macOS
   brew install gh
   
   # Authenticate
   gh auth login
   ```

3. Configure your GitHub username:
   ```bash
   git config --global github.user YOUR_GITHUB_USERNAME
   ```

4. Run the script:
   ```bash
   python3 improved-backup-script.py
   ```

## ⚙️ Configuration

The script backs up paths specified in `CONFIG_PATHS`. You can modify this list in the script to add or remove paths based on your needs:

```python
self.CONFIG_PATHS = [
    '.bashrc',
    '.profile',
    '.gitconfig',
    # ... (see script for complete list)
]
```

## 🛡️ Safety Features

1. **Private Repository**: All backups are stored in a private GitHub repository
2. **Gitignore Patterns**: Sensitive files and directories are excluded
3. **Error Handling**: Robust error handling for file operations
4. **Permission Checks**: Graceful handling of permission-restricted files

## 🔍 Known Limitations

- Does not backup actual virtual environments (only requirements)
- Some configurations may be system-specific
- Large binary files are not suitable for backup
- SSH keys and credentials are intentionally excluded

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Submit a pull request

## ⚠️ Disclaimer

This script modifies your GitHub repositories and local files. While it's designed to be safe:
- Always review the configurations it will backup
- Test in a safe environment first
- Maintain separate backups of critical data
- Use at your own risk

## 📝 License

MIT License - Feel free to use and modify as needed.

## 🙏 Acknowledgments

This project was created by pem725 with assistance from Claude. Special thanks to the Python community for the libraries that make this possible.

---

For more information, bug reports, or feature requests, please open an issue on GitHub.
