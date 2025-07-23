#!/bin/bash

# MAMS Final Cut Pro X Extension Build Script
# Packages the extension for distribution

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
EXTENSION_NAME="MAMS.fxbundle"

echo "🚀 Building MAMS Final Cut Pro X Extension"
echo "Project Directory: $PROJECT_DIR"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Validate extension bundle
echo "🔍 Validating extension bundle..."
BUNDLE_PATH="$PROJECT_DIR/$EXTENSION_NAME"

if [ ! -d "$BUNDLE_PATH" ]; then
    echo "❌ Extension bundle not found: $BUNDLE_PATH"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "Contents/Info.plist"
    "Contents/Resources/Main.html"
    "Contents/Resources/js/app.js"
    "Contents/Resources/js/mams-client.js"
    "Contents/Resources/js/fcpx-api.js"
    "Contents/Resources/css/main.css"
    "Contents/Resources/css/components.css"
)

echo "📋 Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$BUNDLE_PATH/$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
    echo "✅ $file"
done

# Validate Info.plist
echo "🔍 Validating Info.plist..."
if ! plutil -lint "$BUNDLE_PATH/Contents/Info.plist" > /dev/null 2>&1; then
    echo "❌ Invalid Info.plist file"
    exit 1
fi

# Extract version info
VERSION=$(plutil -extract CFBundleShortVersionString raw "$BUNDLE_PATH/Contents/Info.plist")
BUNDLE_ID=$(plutil -extract CFBundleIdentifier raw "$BUNDLE_PATH/Contents/Info.plist")

echo "✅ Extension validation passed"
echo "   Bundle ID: $BUNDLE_ID"
echo "   Version: $VERSION"

# Copy extension bundle to build directory
echo "📦 Copying extension bundle..."
cp -R "$BUNDLE_PATH" "$BUILD_DIR/"

# Copy documentation and supporting files
echo "📄 Copying documentation..."
cp "$PROJECT_DIR/README.md" "$BUILD_DIR/"
cp "$PROJECT_DIR/install.sh" "$BUILD_DIR/"

# Create version info file
echo "📝 Creating version info..."
cat > "$BUILD_DIR/VERSION" << EOF
MAMS Final Cut Pro X Extension
Version: $VERSION
Bundle ID: $BUNDLE_ID
Build Date: $(date)
Build Host: $(hostname)
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
EOF

# Create installation package
echo "📦 Creating installation package..."

# Create ZIP package
cd "$BUILD_DIR"
zip -r "$DIST_DIR/mams-fcpx-extension-v$VERSION.zip" . -x "*.DS_Store"

# Create DMG package (macOS only)
if command -v hdiutil >/dev/null 2>&1; then
    echo "📦 Creating DMG package..."
    
    # Create temporary directory for DMG content
    DMG_TEMP="$BUILD_DIR/dmg_temp"
    mkdir -p "$DMG_TEMP"
    
    # Copy files to DMG directory
    cp -R "$EXTENSION_NAME" "$DMG_TEMP/"
    cp "README.md" "$DMG_TEMP/"
    cp "install.sh" "$DMG_TEMP/"
    
    # Create custom installer script for DMG
    cat > "$DMG_TEMP/Install MAMS Extension.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./install.sh
EOF
    chmod +x "$DMG_TEMP/Install MAMS Extension.command"
    
    # Create DMG
    hdiutil create -srcfolder "$DMG_TEMP" \
                   -volname "MAMS FCPX Extension v$VERSION" \
                   -format UDZO \
                   -o "$DIST_DIR/mams-fcpx-extension-v$VERSION.dmg"
    
    # Clean up temp directory
    rm -rf "$DMG_TEMP"
fi

# Create checksums
echo "🔐 Creating checksums..."
cd "$DIST_DIR"
shasum -a 256 *.zip *.dmg > checksums.sha256 2>/dev/null || true

# Create release notes
echo "📝 Creating release notes..."
cat > "$DIST_DIR/RELEASE_NOTES.md" << EOF
# MAMS Final Cut Pro X Extension v$VERSION

## Release Date
$(date '+%Y-%m-%d')

## Features
- Native Final Cut Pro X integration
- Asset browser with search and filtering
- Direct import to Events with metadata preservation
- Project synchronization with MAMS
- Keyword management and sync
- Preview functionality
- Comprehensive settings management

## Installation

### Automatic Installation
1. Download \`mams-fcpx-extension-v$VERSION.dmg\`
2. Open the DMG file
3. Run "Install MAMS Extension.command"
4. Follow the prompts

### Manual Installation
1. Download \`mams-fcpx-extension-v$VERSION.zip\`
2. Extract the archive
3. Run \`./install.sh\`
4. Follow the prompts

## Requirements
- Final Cut Pro X 10.4 or later
- macOS 10.14 or later
- MAMS server access
- Network connectivity

## Configuration
1. Open Final Cut Pro X
2. Go to **Window** > **Extensions** > **MAMS**
3. Click the settings icon
4. Enter your MAMS server URL and credentials
5. Test the connection
6. Start importing assets!

## File Checksums
\`\`\`
$(cat checksums.sha256 2>/dev/null || echo "Checksums not available")
\`\`\`

## Support
- Documentation: https://docs.mams.io/fcpx
- Support: support@mams.io
- Issues: https://github.com/mams/fcpx-extension/issues
EOF

# Validate the built extension
echo "🔍 Validating built extension..."
BUILT_BUNDLE="$BUILD_DIR/$EXTENSION_NAME"

# Check bundle structure
if [ ! -d "$BUILT_BUNDLE/Contents" ]; then
    echo "❌ Invalid bundle structure"
    exit 1
fi

# Check Info.plist again
if ! plutil -lint "$BUILT_BUNDLE/Contents/Info.plist" > /dev/null 2>&1; then
    echo "❌ Built bundle has invalid Info.plist"
    exit 1
fi

# Check file permissions
if [ ! -r "$BUILT_BUNDLE/Contents/Resources/Main.html" ]; then
    echo "❌ Main.html is not readable"
    exit 1
fi

echo "✅ Extension validation passed"

# Build summary
echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📦 Packages created:"
ls -la "$DIST_DIR"/*.zip "$DIST_DIR"/*.dmg 2>/dev/null || true

echo ""
echo "📁 Build artifacts:"
echo "   Build directory: $BUILD_DIR"
echo "   Distribution: $DIST_DIR"
echo "   Extension: $BUILT_BUNDLE"
echo "   Version: $VERSION"

echo ""
echo "🚀 Ready for distribution!"

echo ""
echo "📋 Installation Instructions:"
echo "   1. Extract the ZIP or mount the DMG"
echo "   2. Run the installer script"
echo "   3. Open Final Cut Pro X"
echo "   4. Access via Window > Extensions > MAMS"