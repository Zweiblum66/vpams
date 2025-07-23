/**
 * MAMS Mobile Application
 * 
 * Main App component that sets up navigation, state management,
 * and provides the application context.
 */

import React, {useEffect} from 'react';
import {StatusBar, LogBox} from 'react-native';
import {Provider as PaperProvider} from 'react-native-paper';
import {Provider as ReduxProvider} from 'react-redux';
import {PersistGate} from 'redux-persist/integration/react';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {NavigationContainer} from '@react-navigation/native';
import SplashScreen from 'react-native-splash-screen';
import FlashMessage from 'react-native-flash-message';

import {store, persistor} from '@/store';
import {AppNavigator} from '@/navigation/AppNavigator';
import {theme} from '@/constants/theme';
import {LoadingScreen} from '@/components/LoadingScreen';
import {ErrorBoundary} from '@/components/ErrorBoundary';
import {NetworkProvider} from '@/providers/NetworkProvider';
import {AuthProvider} from '@/providers/AuthProvider';

// Ignore specific warnings for better development experience
LogBox.ignoreLogs([
  'Warning: AsyncStorage has been extracted',
  'Remote debugger',
  'Setting a timer',
]);

const App: React.FC = () => {
  useEffect(() => {
    // Hide splash screen once app is ready
    const timer = setTimeout(() => {
      SplashScreen.hide();
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <ErrorBoundary>
      <ReduxProvider store={store}>
        <PersistGate loading={<LoadingScreen />} persistor={persistor}>
          <PaperProvider theme={theme}>
            <SafeAreaProvider>
              <NetworkProvider>
                <AuthProvider>
                  <NavigationContainer theme={theme}>
                    <StatusBar
                      barStyle="dark-content"
                      backgroundColor={theme.colors.background}
                      translucent={false}
                    />
                    <AppNavigator />
                    <FlashMessage position="top" />
                  </NavigationContainer>
                </AuthProvider>
              </NetworkProvider>
            </SafeAreaProvider>
          </PaperProvider>
        </PersistGate>
      </ReduxProvider>
    </ErrorBoundary>
  );
};

export default App;