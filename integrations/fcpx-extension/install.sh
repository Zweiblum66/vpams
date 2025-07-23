#!/bin/bash

# MAMS Final Cut Pro X Extension Installer
# Installs the MAMS extension to the correct location

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_NAME="MAMS.fxbundle"
SOURCE_PATH="$SCRIPT_DIR/$EXTENSION_NAME"

# Determine installation path
if [[ "$OSTYPE" == "darwin"* ]]; then
    INSTALL_PATH="$HOME/Library/Application Support/ProApps/Extensions"
else
    echo "❌ This extension is only compatible with macOS"
    exit 1
fi

echo "🚀 MAMS Final Cut Pro X Extension Installer"
echo "=========================================="

# Check if Final Cut Pro X is installed
FCPX_PATH="/Applications/Final Cut Pro.app"
if [ ! -d "$FCPX_PATH" ]; then
    echo "⚠️  Final Cut Pro X not found at $FCPX_PATH"
    echo "   Please install Final Cut Pro X before continuing"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check FCPX version
if [ -d "$FCPX_PATH" ]; then
    FCPX_VERSION=$(defaults read "$FCPX_PATH/Contents/Info" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
    echo "📱 Final Cut Pro X version: $FCPX_VERSION"
    
    # Check minimum version requirement (10.4.0)
    if [[ "$FCPX_VERSION" < "10.4.0" ]] && [[ "$FCPX_VERSION" != "Unknown" ]]; then
        echo "⚠️  Final Cut Pro X 10.4.0 or later is required"
        echo "   Current version: $FCPX_VERSION"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Check if source extension exists
if [ ! -d "$SOURCE_PATH" ]; then
    echo "❌ Extension bundle not found at: $SOURCE_PATH"
    echo "   Please ensure the extension is built correctly"
    exit 1
fi

echo "📦 Extension bundle found: $SOURCE_PATH"
echo "📁 Installation path: $INSTALL_PATH"

# Create installation directory
echo "📁 Creating installation directory..."
mkdir -p "$INSTALL_PATH"

# Check if extension is already installed
DEST_PATH="$INSTALL_PATH/$EXTENSION_NAME"
if [ -d "$DEST_PATH" ]; then
    echo "⚠️  Extension already installed at: $DEST_PATH"
    read -p "Replace existing installation? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing installation..."
        rm -rf "$DEST_PATH"
    else
        echo "Installation cancelled"
        exit 0
    fi
fi

# Copy extension
echo "📦 Installing extension..."
cp -R "$SOURCE_PATH" "$DEST_PATH"

# Set proper permissions
echo "🔒 Setting permissions..."
chmod -R 755 "$DEST_PATH"

# Verify installation
if [ -d "$DEST_PATH" ]; then
    echo "✅ Extension installed successfully!"
    echo
    echo "📋 Next Steps:"
    echo "1. Start Final Cut Pro X"
    echo "2. Go to Window > Extensions > MAMS"
    echo "3. Configure your MAMS server connection"
    echo "4. Start importing assets!"
    echo
    echo "📚 Documentation:"
    echo "   README.md - Complete usage guide"
    echo "   Support: https://docs.mams.io/fcpx"
    echo
    
    # Ask to open Final Cut Pro X
    read -p "Open Final Cut Pro X now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$FCPX_PATH"
    fi
    
else
    echo "❌ Installation failed"
    exit 1
fi

echo "🎉 Installation complete!"