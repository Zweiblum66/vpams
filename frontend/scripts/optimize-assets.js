#!/usr/bin/env node

/**
 * Asset optimization script for MAMS frontend
 * Optimizes images, fonts, and other static assets
 */

import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';
import { glob } from 'glob';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const config = {
  inputDir: path.join(__dirname, '../src/assets'),
  outputDir: path.join(__dirname, '../dist/assets'),
  imageQuality: {
    jpeg: 85,
    webp: 85,
    avif: 80,
    png: 90
  },
  imageFormats: ['webp', 'original'],
  imageSizes: {
    thumbnail: [150, 150],
    small: [300, 200],
    medium: [600, 400],
    large: [1200, 800],
    xl: [1920, 1080]
  }
};

class AssetOptimizer {
  constructor() {
    this.stats = {
      processed: 0,
      optimized: 0,
      saved: 0,
      errors: 0
    };
  }

  async optimize() {
    console.log('🚀 Starting asset optimization...');
    
    try {
      await this.ensureDirectories();
      await this.optimizeImages();
      await this.optimizeFonts();
      await this.optimizeIcons();
      await this.generateManifest();
      
      this.printSummary();
    } catch (error) {
      console.error('❌ Optimization failed:', error);
      process.exit(1);
    }
  }

  async ensureDirectories() {
    const dirs = [
      path.join(config.outputDir, 'images'),
      path.join(config.outputDir, 'fonts'),
      path.join(config.outputDir, 'icons')
    ];

    for (const dir of dirs) {
      await fs.mkdir(dir, { recursive: true });
    }
  }

  async optimizeImages() {
    console.log('📸 Optimizing images...');
    
    const imagePatterns = [
      path.join(config.inputDir, 'images/**/*.{jpg,jpeg,png,gif,svg}'),
      path.join(config.inputDir, '**/*.{jpg,jpeg,png,gif}')
    ];

    for (const pattern of imagePatterns) {
      const files = await glob(pattern);
      
      for (const file of files) {
        await this.processImage(file);
      }
    }
  }

  async processImage(filePath) {
    try {
      this.stats.processed++;
      
      const ext = path.extname(filePath).toLowerCase();
      const basename = path.basename(filePath, ext);
      const relativePath = path.relative(config.inputDir, path.dirname(filePath));
      const outputDir = path.join(config.outputDir, relativePath);
      
      await fs.mkdir(outputDir, { recursive: true });

      if (ext === '.svg') {
        // Copy SVG files as-is (could add optimization here)
        await fs.copyFile(filePath, path.join(outputDir, path.basename(filePath)));
        return;
      }

      if (ext === '.gif') {
        // Copy GIF files as-is (animated images)
        await fs.copyFile(filePath, path.join(outputDir, path.basename(filePath)));
        return;
      }

      const originalStats = await fs.stat(filePath);
      const image = sharp(filePath);
      const metadata = await image.metadata();
      
      // Generate multiple formats and sizes
      for (const format of config.imageFormats) {
        if (format === 'original') {
          await this.optimizeOriginalFormat(image, filePath, outputDir, basename, ext);
        } else {
          await this.generateWebPVariant(image, outputDir, basename);
        }
      }
      
      // Generate responsive sizes for large images
      if (metadata.width > 600) {
        await this.generateResponsiveSizes(image, outputDir, basename);
      }
      
      this.stats.optimized++;
      
    } catch (error) {
      console.error(`❌ Failed to process ${filePath}:`, error.message);
      this.stats.errors++;
    }
  }

  async optimizeOriginalFormat(image, filePath, outputDir, basename, ext) {
    const outputPath = path.join(outputDir, `${basename}${ext}`);
    
    let processor = image.clone();
    
    switch (ext) {
      case '.jpg':
      case '.jpeg':
        processor = processor.jpeg({ 
          quality: config.imageQuality.jpeg,
          progressive: true,
          mozjpeg: true 
        });
        break;
        
      case '.png':
        processor = processor.png({ 
          quality: config.imageQuality.png,
          progressive: true,
          compressionLevel: 9
        });
        break;
    }
    
    await processor.toFile(outputPath);
    
    // Calculate savings
    const originalSize = (await fs.stat(filePath)).size;
    const optimizedSize = (await fs.stat(outputPath)).size;
    const saved = originalSize - optimizedSize;
    
    if (saved > 0) {
      this.stats.saved += saved;
      console.log(`  ✅ ${basename}${ext}: ${this.formatBytes(saved)} saved`);
    }
  }

  async generateWebPVariant(image, outputDir, basename) {
    const outputPath = path.join(outputDir, `${basename}.webp`);
    
    await image
      .clone()
      .webp({ 
        quality: config.imageQuality.webp,
        effort: 6 
      })
      .toFile(outputPath);
  }

  async generateResponsiveSizes(image, outputDir, basename) {
    for (const [sizeName, [width, height]] of Object.entries(config.imageSizes)) {
      const outputPath = path.join(outputDir, `${basename}-${sizeName}.webp`);
      
      await image
        .clone()
        .resize(width, height, { 
          fit: 'inside',
          withoutEnlargement: true 
        })
        .webp({ quality: config.imageQuality.webp })
        .toFile(outputPath);
    }
  }

  async optimizeFonts() {
    console.log('🔤 Processing fonts...');
    
    const fontFiles = await glob(path.join(config.inputDir, 'fonts/**/*.{woff,woff2,ttf,eot}'));
    
    for (const fontFile of fontFiles) {
      const outputPath = path.join(
        config.outputDir, 
        'fonts', 
        path.basename(fontFile)
      );
      
      await fs.copyFile(fontFile, outputPath);
      this.stats.processed++;
    }
  }

  async optimizeIcons() {
    console.log('🎯 Processing icons...');
    
    const iconFiles = await glob(path.join(config.inputDir, 'icons/**/*.{svg,png,ico}'));
    
    for (const iconFile of iconFiles) {
      const ext = path.extname(iconFile);
      const basename = path.basename(iconFile, ext);
      const outputDir = path.join(config.outputDir, 'icons');
      
      if (ext === '.svg') {
        // Copy SVG icons as-is
        await fs.copyFile(iconFile, path.join(outputDir, path.basename(iconFile)));
      } else if (ext === '.png') {
        // Optimize PNG icons
        const sizes = [16, 32, 48, 64, 128, 256];
        
        for (const size of sizes) {
          const outputPath = path.join(outputDir, `${basename}-${size}x${size}.png`);
          
          await sharp(iconFile)
            .resize(size, size)
            .png({ quality: 100, compressionLevel: 9 })
            .toFile(outputPath);
        }
      } else {
        // Copy other formats as-is
        await fs.copyFile(iconFile, path.join(outputDir, path.basename(iconFile)));
      }
      
      this.stats.processed++;
    }
  }

  async generateManifest() {
    console.log('📄 Generating asset manifest...');
    
    const manifest = {
      version: Date.now(),
      timestamp: new Date().toISOString(),
      images: {},
      fonts: {},
      icons: {}
    };

    // Scan optimized assets
    const imageFiles = await glob(path.join(config.outputDir, 'images/**/*'));
    const fontFiles = await glob(path.join(config.outputDir, 'fonts/**/*'));
    const iconFiles = await glob(path.join(config.outputDir, 'icons/**/*'));

    // Build image manifest
    for (const file of imageFiles) {
      const stats = await fs.stat(file);
      const relativePath = path.relative(config.outputDir, file);
      const key = path.basename(file, path.extname(file));
      
      if (!manifest.images[key]) {
        manifest.images[key] = [];
      }
      
      manifest.images[key].push({
        path: `/${relativePath.replace(/\\/g, '/')}`,
        size: stats.size,
        format: path.extname(file).slice(1),
        mtime: stats.mtime.toISOString()
      });
    }

    // Build font manifest
    for (const file of fontFiles) {
      const stats = await fs.stat(file);
      const relativePath = path.relative(config.outputDir, file);
      const key = path.basename(file, path.extname(file));
      
      manifest.fonts[key] = {
        path: `/${relativePath.replace(/\\/g, '/')}`,
        size: stats.size,
        format: path.extname(file).slice(1),
        mtime: stats.mtime.toISOString()
      };
    }

    // Build icon manifest
    for (const file of iconFiles) {
      const stats = await fs.stat(file);
      const relativePath = path.relative(config.outputDir, file);
      const key = path.basename(file, path.extname(file));
      
      if (!manifest.icons[key]) {
        manifest.icons[key] = [];
      }
      
      manifest.icons[key].push({
        path: `/${relativePath.replace(/\\/g, '/')}`,
        size: stats.size,
        format: path.extname(file).slice(1),
        mtime: stats.mtime.toISOString()
      });
    }

    await fs.writeFile(
      path.join(config.outputDir, 'manifest.json'),
      JSON.stringify(manifest, null, 2)
    );
  }

  printSummary() {
    console.log('\n📊 Optimization Summary:');
    console.log(`   Files processed: ${this.stats.processed}`);
    console.log(`   Files optimized: ${this.stats.optimized}`);
    console.log(`   Bytes saved: ${this.formatBytes(this.stats.saved)}`);
    console.log(`   Errors: ${this.stats.errors}`);
    
    if (this.stats.saved > 0) {
      const percentage = ((this.stats.saved / (this.stats.saved + 1000000)) * 100).toFixed(1);
      console.log(`   Space reduction: ~${percentage}%`);
    }
    
    console.log('\n✅ Asset optimization complete!');
  }

  formatBytes(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }
}

// CLI interface
if (import.meta.url === `file://${process.argv[1]}`) {
  const optimizer = new AssetOptimizer();
  
  // Parse command line arguments
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: node optimize-assets.js [options]

Options:
  --input <dir>    Input directory (default: src/assets)
  --output <dir>   Output directory (default: dist/assets)
  --quality <num>  JPEG quality 1-100 (default: 85)
  --formats <list> Output formats: webp,avif,original (default: webp,original)
  --sizes <list>   Generate responsive sizes (default: enabled)
  --help, -h       Show this help message

Examples:
  node optimize-assets.js
  node optimize-assets.js --quality 90 --formats webp,avif,original
  node optimize-assets.js --input ./assets --output ./optimized
    `);
    process.exit(0);
  }

  // Parse options
  for (let i = 0; i < args.length; i += 2) {
    const option = args[i];
    const value = args[i + 1];
    
    switch (option) {
      case '--input':
        config.inputDir = path.resolve(value);
        break;
      case '--output':
        config.outputDir = path.resolve(value);
        break;
      case '--quality':
        const quality = parseInt(value);
        if (quality >= 1 && quality <= 100) {
          config.imageQuality.jpeg = quality;
          config.imageQuality.webp = quality;
        }
        break;
      case '--formats':
        config.imageFormats = value.split(',');
        break;
    }
  }

  optimizer.optimize().catch(console.error);
}

export default AssetOptimizer;