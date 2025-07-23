#!/bin/bash

# MAMS Avid Media Composer Plugin Build Script

echo "Building MAMS Avid Media Composer Plugin..."

# Check for required tools
if ! command -v cmake &> /dev/null; then
    echo "Error: cmake is required but not installed."
    exit 1
fi

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    PLUGIN_EXT=".bundle"
    INSTALL_PATH="/Library/Application Support/Avid"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="Windows"
    PLUGIN_EXT=".dll"
    INSTALL_PATH="C:/Program Files/Avid"
else
    echo "Error: Unsupported platform"
    exit 1
fi

echo "Building for $PLATFORM..."

# Create build directories
mkdir -p build/ama
mkdir -p build/console
mkdir -p dist

# Build AMA Plugin
echo "Building AMA Plugin..."
cd build/ama
cmake ../../ama-plugin
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
cd ../..

# Build Console Plugin
echo "Building Console Plugin..."
cd build/console
cmake ../../console-plugin
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
cd ../..

# Copy binaries to dist
echo "Copying binaries..."
if [[ "$PLATFORM" == "macOS" ]]; then
    cp -r build/ama/bin/MAMS_AMA.bundle dist/
    cp -r build/console/bin/MAMS_Console.bundle dist/
else
    cp build/ama/bin/MAMS_AMA.dll dist/
    cp build/console/bin/MAMS_Console.dll dist/
fi

# Copy panel files
echo "Copying panel files..."
cp -r panel dist/

# Create installer package
echo "Creating installer package..."
cat > dist/install.sh << 'EOF'
#!/bin/bash

echo "MAMS Avid Plugin Installer"
echo "========================="

# Check if Avid is installed
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVID_PATH="/Applications/Avid Media Composer.app"
    AMA_PATH="/Library/Application Support/Avid/AMA/Plug-ins"
    AVX_PATH="/Library/Application Support/Avid/AVX2/Plug-ins"
    PANEL_PATH="/Library/Application Support/Avid/Panels"
else
    AVID_PATH="C:/Program Files/Avid/Media Composer"
    AMA_PATH="C:/Program Files/Avid/AMA_Plug-ins"
    AVX_PATH="C:/Program Files/Avid/AVX2_Plug-ins"
    PANEL_PATH="C:/Program Files/Avid/Panels"
fi

if [ ! -d "$AVID_PATH" ]; then
    echo "Error: Avid Media Composer not found"
    exit 1
fi

# Create directories if needed
echo "Creating plugin directories..."
sudo mkdir -p "$AMA_PATH"
sudo mkdir -p "$AVX_PATH"
sudo mkdir -p "$PANEL_PATH/MAMS"

# Copy plugins
echo "Installing AMA plugin..."
sudo cp -r MAMS_AMA.* "$AMA_PATH/"

echo "Installing Console plugin..."
sudo cp -r MAMS_Console.* "$AVX_PATH/"

echo "Installing panel..."
sudo cp -r panel/* "$PANEL_PATH/MAMS/"

# Set permissions
if [[ "$OSTYPE" == "darwin"* ]]; then
    sudo chmod -R 755 "$AMA_PATH/MAMS_AMA.bundle"
    sudo chmod -R 755 "$AVX_PATH/MAMS_Console.bundle"
    sudo chmod -R 755 "$PANEL_PATH/MAMS"
fi

echo "Installation complete!"
echo "Please restart Avid Media Composer to use the MAMS plugin."
EOF

chmod +x dist/install.sh

# Create README
cat > dist/README.txt << 'EOF'
MAMS Avid Media Composer Plugin
==============================

Installation:
1. Close Avid Media Composer if running
2. Run install.sh (macOS/Linux) or install.bat (Windows)
3. Restart Avid Media Composer
4. Access MAMS features through:
   - Tools > MAMS > Asset Browser (Panel)
   - Console commands (MAMS.*)
   - Link to AMA Volume > MAMS

Configuration:
1. Open the MAMS panel
2. Click Settings
3. Enter your MAMS server URL and API key
4. Save settings

For more information, visit: https://docs.mams.io/avid
EOF

echo "Build complete! Output in dist/ directory"
echo ""
echo "To install:"
echo "1. cd dist"
echo "2. ./install.sh"