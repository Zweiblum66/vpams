const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration for React Native
 * https://facebook.github.io/metro/docs/configuration
 *
 * @type {import('metro-config').MetroConfig}
 */
const config = {
  transformer: {
    babelTransformerPath: require.resolve('react-native-svg-transformer'),
  },
  resolver: {
    assetExts: ['bin', 'txt', 'jpg', 'png', 'json', 'mp4', 'mov', 'avi', 'mkv', 'mp3', 'wav', 'aac', 'flac'],
    sourceExts: ['js', 'json', 'ts', 'tsx', 'jsx', 'svg'],
    alias: {
      '@': './src',
      '@/components': './src/components',
      '@/screens': './src/screens',
      '@/services': './src/services',
      '@/store': './src/store',
      '@/types': './src/types',
      '@/utils': './src/utils',
      '@/assets': './src/assets',
      '@/hooks': './src/hooks',
      '@/navigation': './src/navigation',
      '@/constants': './src/constants',
    },
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);