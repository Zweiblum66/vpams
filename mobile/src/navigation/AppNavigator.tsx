/**
 * MAMS Mobile App Navigator
 * 
 * Main navigation component that handles routing between
 * authenticated and non-authenticated screens.
 */

import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';
import {useSelector} from 'react-redux';

import {RootStackParamList} from '@/types';
import {AppState} from '@/types';
import {AuthStack} from './AuthStack';
import {MainStack} from './MainStack';
import {LoadingScreen} from '@/components/LoadingScreen';

const Stack = createStackNavigator<RootStackParamList>();

export const AppNavigator: React.FC = () => {
  const {isAuthenticated, isLoading} = useSelector((state: AppState) => state.auth);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <Stack.Navigator screenOptions={{headerShown: false}}>
      {isAuthenticated ? (
        <Stack.Screen name="MainTabs" component={MainStack} />
      ) : (
        <Stack.Screen name="Login" component={AuthStack} />
      )}
    </Stack.Navigator>
  );
};