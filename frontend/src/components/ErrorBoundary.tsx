import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Container, Alert, Collapse, IconButton } from '@mui/material';
import { RefreshRounded as RefreshIcon, ExpandMore, ExpandLess, BugReport } from '@mui/icons-material';
import { logger } from '../utils/logger';
import { errorReportingService } from '../services/errorReportingService';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  errorId: string | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      showDetails: false,
      errorId: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    return { hasError: true, error, errorInfo: null, errorId };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error with comprehensive context
    logger.fatal('React error boundary caught error', {
      errorId: this.state.errorId,
      errorMessage: error.message,
      errorStack: error.stack,
      componentStack: errorInfo.componentStack,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    }, error);

    this.setState({
      error,
      errorInfo,
    });

    // Report error to error reporting service
    errorReportingService.reportError(error, {
      errorId: this.state.errorId,
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    });
  }

  handleRefresh = () => {
    logger.info('User refreshed page after error', { errorId: this.state.errorId });
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false, errorId: null });
    window.location.reload();
  };

  toggleDetails = () => {
    this.setState(prevState => ({ showDetails: !prevState.showDetails }));
  };

  reportError = () => {
    if (this.state.error && this.state.errorId) {
      logger.info('User reported error', { errorId: this.state.errorId });
      // Here you could integrate with a bug reporting service
      // For now, we'll just copy error details to clipboard
      const errorReport = {
        errorId: this.state.errorId,
        message: this.state.error.message,
        stack: this.state.error.stack,
        componentStack: this.state.errorInfo?.componentStack,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
      };
      
      navigator.clipboard.writeText(JSON.stringify(errorReport, null, 2))
        .then(() => {
          alert('Error details copied to clipboard. Please share this with support.');
        })
        .catch(() => {
          alert('Failed to copy error details. Please manually copy the error information.');
        });
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container maxWidth="md" sx={{ mt: 4 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Something went wrong
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              An unexpected error occurred. Please try refreshing the page.
            </Typography>
            {this.state.errorId && (
              <Typography variant="caption" color="text.secondary">
                Error ID: {this.state.errorId}
              </Typography>
            )}
          </Alert>
          
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mb: 3, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={this.handleRefresh}
            >
              Refresh Page
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<BugReport />}
              onClick={this.reportError}
            >
              Report Error
            </Button>
            
            <Button
              variant="text"
              startIcon={this.state.showDetails ? <ExpandLess /> : <ExpandMore />}
              onClick={this.toggleDetails}
            >
              {this.state.showDetails ? 'Hide' : 'Show'} Details
            </Button>
          </Box>
          
          <Collapse in={this.state.showDetails}>
            {this.state.error && (
              <Box sx={{ 
                backgroundColor: 'grey.100', 
                p: 2, 
                borderRadius: 1,
                overflow: 'auto',
                mb: 2
              }}>
                <Typography variant="subtitle2" gutterBottom>
                  Error Details:
                </Typography>
                <Typography variant="body2" component="pre" sx={{ fontSize: '0.8rem', mb: 2 }}>
                  {this.state.error.toString()}
                </Typography>
                
                {this.state.error.stack && (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      Stack Trace:
                    </Typography>
                    <Typography variant="body2" component="pre" sx={{ fontSize: '0.8rem', mb: 2 }}>
                      {this.state.error.stack}
                    </Typography>
                  </>
                )}
                
                {this.state.errorInfo && (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      Component Stack:
                    </Typography>
                    <Typography variant="body2" component="pre" sx={{ fontSize: '0.8rem' }}>
                      {this.state.errorInfo.componentStack}
                    </Typography>
                  </>
                )}
              </Box>
            )}
          </Collapse>
        </Container>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;