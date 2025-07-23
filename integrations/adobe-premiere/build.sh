#!/bin/bash

# MAMS Premiere Pro Panel Build Script

echo "Building MAMS Premiere Pro Panel..."

# Clean previous build
rm -rf dist
mkdir -p dist

# Copy extension files
cp -r CSXS dist/
cp -r host dist/
cp -r icons dist/

# Build client
cd client
npm install
npm run build
cd ..

# Copy client build to dist
cp -r client/dist/* dist/client/

# Create .debug file for development
cat > dist/.debug <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<ExtensionList>
    <Extension Id="com.mams.premiere.panel">
        <HostList>
            <Host Name="PPRO" Port="7777"/>
        </HostList>
    </Extension>
</ExtensionList>
EOF

# Create ZXP package (requires ZXPSignCmd)
# Uncomment if you have ZXPSignCmd installed
# ZXPSignCmd -sign dist mams-premiere-panel.zxp cert.p12 password -tsa http://timestamp.digicert.com

echo "Build complete! Extension is in the 'dist' folder."
echo ""
echo "To install for development:"
echo "1. Enable debug mode in Creative Cloud"
echo "2. Copy the 'dist' folder to:"
echo "   - macOS: ~/Library/Application Support/Adobe/CEP/extensions/com.mams.premiere"
echo "   - Windows: %APPDATA%\\Adobe\\CEP\\extensions\\com.mams.premiere"
echo ""
echo "Then restart Premiere Pro and find 'MAMS' in Window > Extensions menu."