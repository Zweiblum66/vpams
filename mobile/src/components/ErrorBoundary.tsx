/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the component tree
 * and displays a fallback UI instead of crashing the app.
 */

import React, {Component, ReactNode} from 'react';
import {View, StyleSheet} from 'react-native';
import {Text, Button, Card} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {colors, spacing, typography} from '@/constants/theme';
import {errorReportingService} from '@/services/errorReportingService';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: any;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Report error to crash reporting service
    errorReportingService.reportError(error, {
      componentStack: errorInfo.componentStack,
      severity: 'critical',
    });
  }

  handleRestart = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Card style={styles.errorCard}>
            <Card.Content style={styles.cardContent}>
              <Icon name="error-outline" size={64} color={colors.error} />
              
              <Text style={styles.title}>Oops! Something went wrong</Text>
              
              <Text style={styles.message}>
                The app encountered an unexpected error and needs to restart.
              </Text>
              
              {__DEV__ && this.state.error && (
                <View style={styles.debugContainer}>
                  <Text style={styles.debugTitle}>Debug Information:</Text>
                  <Text style={styles.debugText}>{this.state.error.toString()}</Text>
                  {this.state.errorInfo && (
                    <Text style={styles.debugText}>
                      {this.state.errorInfo.componentStack}
                    </Text>
                  )}
                </View>
              )}
              
              <Button
                mode="contained"
                onPress={this.handleRestart}
                style={styles.restartButton}
                contentStyle={styles.restartButtonContent}>
                Restart App
              </Button>
            </Card.Content>
          </Card>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  errorCard: {
    width: '100%',
    maxWidth: 400,
  },
  cardContent: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  title: {
    ...typography.headlineSmall,
    color: colors.error,
    textAlign: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  message: {
    ...typography.bodyLarge,
    color: colors.onSurface,
    textAlign: 'center',
    marginBottom: spacing.lg,
    lineHeight: 24,
  },
  debugContainer: {
    backgroundColor: colors.gray100,
    padding: spacing.md,
    borderRadius: 8,
    marginBottom: spacing.lg,
    width: '100%',
  },
  debugTitle: {
    ...typography.labelLarge,
    color: colors.onSurface,
    marginBottom: spacing.xs,
    fontWeight: '600',
  },
  debugText: {
    ...typography.bodySmall,
    color: colors.gray700,
    fontFamily: 'monospace',
    marginBottom: spacing.xs,
  },
  restartButton: {
    width: '100%',
  },
  restartButtonContent: {
    paddingVertical: spacing.xs,
  },
});