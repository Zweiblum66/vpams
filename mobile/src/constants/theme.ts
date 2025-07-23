/**
 * MAMS Mobile Theme Configuration
 * 
 * Defines the design system for the mobile application including
 * colors, typography, spacing, and component styles.
 */

import {MD3LightTheme, MD3DarkTheme} from 'react-native-paper';
import {DefaultTheme as NavigationLightTheme, DarkTheme as NavigationDarkTheme} from '@react-navigation/native';

// MAMS Brand Colors
export const colors = {
  primary: '#1976D2',
  primaryVariant: '#1565C0',
  secondary: '#FFA000',
  secondaryVariant: '#FF8F00',
  background: '#FFFFFF',
  surface: '#F5F5F5',
  error: '#D32F2F',
  warning: '#F57C00',
  success: '#388E3C',
  info: '#1976D2',
  
  // Text colors
  onPrimary: '#FFFFFF',
  onSecondary: '#000000',
  onBackground: '#212121',
  onSurface: '#212121',
  onError: '#FFFFFF',
  
  // Gray scale
  gray50: '#FAFAFA',
  gray100: '#F5F5F5',
  gray200: '#EEEEEE',
  gray300: '#E0E0E0',
  gray400: '#BDBDBD',
  gray500: '#9E9E9E',
  gray600: '#757575',
  gray700: '#616161',
  gray800: '#424242',
  gray900: '#212121',
  
  // Media specific colors
  video: '#E91E63',
  audio: '#9C27B0',
  image: '#4CAF50',
  document: '#FF9800',
  
  // Status colors
  draft: '#757575',
  processing: '#FF9800',
  approved: '#4CAF50',
  rejected: '#F44336',
  archived: '#9E9E9E',
};

// Light theme configuration
export const lightTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.primary,
    primaryContainer: colors.primaryVariant,
    secondary: colors.secondary,
    secondaryContainer: colors.secondaryVariant,
    background: colors.background,
    surface: colors.surface,
    error: colors.error,
    onPrimary: colors.onPrimary,
    onSecondary: colors.onSecondary,
    onBackground: colors.onBackground,
    onSurface: colors.onSurface,
    onError: colors.onError,
  },
};

// Dark theme configuration
export const darkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: '#42A5F5',
    primaryContainer: '#1976D2',
    secondary: '#FFB74D',
    secondaryContainer: '#FF8F00',
    background: '#121212',
    surface: '#1E1E1E',
    error: '#EF5350',
    onPrimary: '#000000',
    onSecondary: '#000000',
    onBackground: '#FFFFFF',
    onSurface: '#FFFFFF',
    onError: '#000000',
  },
};

// Navigation themes
export const navigationLightTheme = {
  ...NavigationLightTheme,
  colors: {
    ...NavigationLightTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.onBackground,
    border: colors.gray200,
  },
};

export const navigationDarkTheme = {
  ...NavigationDarkTheme,
  colors: {
    ...NavigationDarkTheme.colors,
    primary: '#42A5F5',
    background: '#121212',
    card: '#1E1E1E',
    text: '#FFFFFF',
    border: '#333333',
  },
};

// Typography
export const typography = {
  // Display styles
  displayLarge: {
    fontSize: 57,
    lineHeight: 64,
    fontWeight: '400' as const,
    letterSpacing: -0.25,
  },
  displayMedium: {
    fontSize: 45,
    lineHeight: 52,
    fontWeight: '400' as const,
    letterSpacing: 0,
  },
  displaySmall: {
    fontSize: 36,
    lineHeight: 44,
    fontWeight: '400' as const,
    letterSpacing: 0,
  },
  
  // Headline styles
  headlineLarge: {
    fontSize: 32,
    lineHeight: 40,
    fontWeight: '400' as const,
    letterSpacing: 0,
  },
  headlineMedium: {
    fontSize: 28,
    lineHeight: 36,
    fontWeight: '400' as const,
    letterSpacing: 0,
  },
  headlineSmall: {
    fontSize: 24,
    lineHeight: 32,
    fontWeight: '400' as const,
    letterSpacing: 0,
  },
  
  // Title styles
  titleLarge: {
    fontSize: 22,
    lineHeight: 28,
    fontWeight: '500' as const,
    letterSpacing: 0,
  },
  titleMedium: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '500' as const,
    letterSpacing: 0.1,
  },
  titleSmall: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '500' as const,
    letterSpacing: 0.1,
  },
  
  // Body styles
  bodyLarge: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '400' as const,
    letterSpacing: 0.15,
  },
  bodyMedium: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400' as const,
    letterSpacing: 0.25,
  },
  bodySmall: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '400' as const,
    letterSpacing: 0.4,
  },
  
  // Label styles
  labelLarge: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '500' as const,
    letterSpacing: 0.1,
  },
  labelMedium: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '500' as const,
    letterSpacing: 0.5,
  },
  labelSmall: {
    fontSize: 11,
    lineHeight: 16,
    fontWeight: '500' as const,
    letterSpacing: 0.5,
  },
};

// Spacing system
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
};

// Border radius
export const borderRadius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

// Shadows
export const shadows = {
  none: {
    shadowOffset: {width: 0, height: 0},
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.18,
    shadowRadius: 1.0,
    elevation: 1,
  },
  md: {
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.23,
    shadowRadius: 2.62,
    elevation: 4,
  },
  lg: {
    shadowOffset: {width: 0, height: 4},
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
    elevation: 8,
  },
  xl: {
    shadowOffset: {width: 0, height: 6},
    shadowOpacity: 0.37,
    shadowRadius: 7.49,
    elevation: 12,
  },
};

// Export default theme (light theme)
export const theme = lightTheme;