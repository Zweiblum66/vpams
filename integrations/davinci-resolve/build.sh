#!/bin/bash

# MAMS DaVinci Resolve Integration Build Script
# Packages the integration for distribution

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
VERSION=$(grep -o '"version": "[^"]*"' "$PROJECT_DIR/package.json" | cut -d'"' -f4)

echo "🚀 Building MAMS DaVinci Resolve Integration v$VERSION"
echo "Project Directory: $PROJECT_DIR"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Copy source files
echo "📦 Copying source files..."
cp -r "$PROJECT_DIR/scripts" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/fusion-scripts" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/utils" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/ui" "$BUILD_DIR/" 2>/dev/null || echo "No UI directory found"

# Copy documentation and metadata
cp "$PROJECT_DIR/README.md" "$BUILD_DIR/"
cp "$PROJECT_DIR/package.json" "$BUILD_DIR/"
cp "$PROJECT_DIR/install.py" "$BUILD_DIR/"

# Copy build script
cp "$PROJECT_DIR/build.sh" "$BUILD_DIR/"

# Create installation package
echo "📦 Creating installation package..."
cd "$BUILD_DIR"

# Create different package formats
echo "Creating ZIP package..."
zip -r "$DIST_DIR/mams-davinci-resolve-v$VERSION.zip" . -x "*.DS_Store" "*.pyc" "__pycache__/*"

echo "Creating TAR.GZ package..."
tar -czf "$DIST_DIR/mams-davinci-resolve-v$VERSION.tar.gz" --exclude="*.DS_Store" --exclude="*.pyc" --exclude="__pycache__" .

# Create platform-specific packages
echo "📦 Creating platform-specific packages..."

# Windows package
echo "Creating Windows package..."
WINDOWS_DIR="$BUILD_DIR/windows"
mkdir -p "$WINDOWS_DIR"
cp -r scripts fusion-scripts utils README.md package.json install.py "$WINDOWS_DIR/"

# Create Windows installer batch file
cat > "$WINDOWS_DIR/install.bat" << 'EOF'
@echo off
echo MAMS DaVinci Resolve Integration Installer
echo ==========================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.6+ from https://python.org
    pause
    exit /b 1
)

python install.py
pause
EOF

cd "$WINDOWS_DIR"
zip -r "$DIST_DIR/mams-davinci-resolve-windows-v$VERSION.zip" . -x "*.DS_Store"
cd "$BUILD_DIR"

# macOS package
echo "Creating macOS package..."
MACOS_DIR="$BUILD_DIR/macos"
mkdir -p "$MACOS_DIR"
cp -r scripts fusion-scripts utils README.md package.json install.py "$MACOS_DIR/"

# Create macOS installer script
cat > "$MACOS_DIR/install.command" << 'EOF'
#!/bin/bash
echo "MAMS DaVinci Resolve Integration Installer"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3 from https://python.org or use Homebrew:"
    echo "brew install python"
    read -p "Press any key to exit..."
    exit 1
fi

# Run installer
cd "$(dirname "$0")"
python3 install.py

echo "Installation complete!"
read -p "Press any key to exit..."
EOF

chmod +x "$MACOS_DIR/install.command"

cd "$MACOS_DIR"
zip -r "$DIST_DIR/mams-davinci-resolve-macos-v$VERSION.zip" . -x "*.DS_Store"
cd "$BUILD_DIR"

# Linux package
echo "Creating Linux package..."
LINUX_DIR="$BUILD_DIR/linux"
mkdir -p "$LINUX_DIR"
cp -r scripts fusion-scripts utils README.md package.json install.py "$LINUX_DIR/"

# Create Linux installer script
cat > "$LINUX_DIR/install.sh" << 'EOF'
#!/bin/bash
echo "MAMS DaVinci Resolve Integration Installer"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3 using your package manager:"
    echo "Ubuntu/Debian: sudo apt install python3"
    echo "CentOS/RHEL: sudo yum install python3"
    echo "Arch: sudo pacman -S python"
    exit 1
fi

# Run installer
cd "$(dirname "$0")"
python3 install.py

echo "Installation complete!"
read -p "Press any key to exit..."
EOF

chmod +x "$LINUX_DIR/install.sh"

cd "$LINUX_DIR"
tar -czf "$DIST_DIR/mams-davinci-resolve-linux-v$VERSION.tar.gz" .
cd "$BUILD_DIR"

# Create checksums
echo "🔐 Creating checksums..."
cd "$DIST_DIR"
shasum -a 256 *.zip *.tar.gz > checksums.sha256

# Create release notes
echo "📝 Creating release notes..."
cat > "$DIST_DIR/RELEASE_NOTES.md" << EOF
# MAMS DaVinci Resolve Integration v$VERSION

## Release Date
$(date '+%Y-%m-%d')

## Features
- Asset browser with search and filtering
- Direct import to Media Pool with metadata
- Project synchronization with MAMS
- Timeline export and import
- Fusion page integration
- Comprehensive settings management

## Installation
1. Download the appropriate package for your platform:
   - Windows: \`mams-davinci-resolve-windows-v$VERSION.zip\`
   - macOS: \`mams-davinci-resolve-macos-v$VERSION.zip\`
   - Linux: \`mams-davinci-resolve-linux-v$VERSION.tar.gz\`
   - Cross-platform: \`mams-davinci-resolve-v$VERSION.zip\`

2. Extract the package
3. Run the installer:
   - Windows: Double-click \`install.bat\`
   - macOS: Double-click \`install.command\`
   - Linux: Run \`./install.sh\`
   - Manual: \`python3 install.py\`

## Requirements
- DaVinci Resolve 17.0 or later (Studio recommended)
- Python 3.6+
- MAMS server access
- Network connectivity

## File Checksums
\`\`\`
$(cat checksums.sha256)
\`\`\`

## Support
- Documentation: https://docs.mams.io/resolve
- Support: support@mams.io
- Issues: https://github.com/mams/resolve-integration/issues
EOF

# Create installation guide
cat > "$DIST_DIR/INSTALLATION_GUIDE.md" << 'EOF'
# MAMS DaVinci Resolve Integration - Installation Guide

## Quick Start

### Windows
1. Download `mams-davinci-resolve-windows-vX.X.X.zip`
2. Extract to a temporary folder
3. Double-click `install.bat`
4. Follow the prompts

### macOS
1. Download `mams-davinci-resolve-macos-vX.X.X.zip`
2. Extract to a temporary folder
3. Double-click `install.command`
4. Follow the prompts

### Linux
1. Download `mams-davinci-resolve-linux-vX.X.X.tar.gz`
2. Extract: `tar -xzf mams-davinci-resolve-linux-vX.X.X.tar.gz`
3. Run: `./install.sh`
4. Follow the prompts

## Manual Installation

If the automatic installer doesn't work, you can install manually:

1. Download the cross-platform package
2. Extract the files
3. Run: `python3 install.py`

## Installation Paths

The installer will place files in these locations:

### Windows
- Scripts: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Scripts\MAMS\`
- Fusion: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\MAMS\`

### macOS
- Scripts: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Scripts/MAMS/`
- Fusion: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/MAMS/`

### Linux
- Scripts: `~/.local/share/DaVinciResolve/scripts/MAMS/`
- Fusion: `~/.local/share/DaVinciResolve/Fusion/Scripts/MAMS/`

## Configuration

After installation:

1. Open DaVinci Resolve
2. Go to **Workspace** > **Scripts** > **MAMS** > **Settings**
3. Enter your MAMS server URL
4. Enter your API key or login credentials
5. Test the connection
6. Configure import preferences

## Verification

To verify the installation:

1. Check that scripts appear in **Workspace** > **Scripts** > **MAMS**
2. Check that Fusion scripts appear in **Scripts** menu on Fusion page
3. Run **MAMS** > **Settings** to test connectivity

## Troubleshooting

### Scripts don't appear
- Restart DaVinci Resolve
- Check installation paths are correct
- Verify Python is installed and accessible

### Connection issues
- Test MAMS server URL in web browser
- Check firewall settings
- Verify API credentials

### Import failures
- Check available disk space
- Verify file permissions
- Test with smaller files first
EOF

# Build summary
echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📦 Packages created:"
ls -la "$DIST_DIR"/*.zip "$DIST_DIR"/*.tar.gz

echo ""
echo "📁 Build artifacts:"
echo "   Build directory: $BUILD_DIR"
echo "   Distribution: $DIST_DIR"
echo "   Version: $VERSION"

echo ""
echo "🚀 Ready for distribution!"