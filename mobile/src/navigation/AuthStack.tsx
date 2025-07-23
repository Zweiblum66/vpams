/**
 * Authentication Stack Navigator
 * 
 * Handles navigation between authentication-related screens
 * including login, registration, and password recovery.
 */

import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';

import {RootStackParamList} from '@/types';
import {LoginScreen} from '@/screens/auth/LoginScreen';
import {RegisterScreen} from '@/screens/auth/RegisterScreen';
import {ForgotPasswordScreen} from '@/screens/auth/ForgotPasswordScreen';

const Stack = createStackNavigator<RootStackParamList>();

export const AuthStack: React.FC = () => {
  return (
    <Stack.Navigator
      initialRouteName="Login"
      screenOptions={{
        headerShown: false,
        gestureEnabled: true,
        cardStyleInterpolator: ({current, layouts}) => {
          return {
            cardStyle: {
              transform: [
                {
                  translateX: current.progress.interpolate({
                    inputRange: [0, 1],
                    outputRange: [layouts.screen.width, 0],
                  }),
                },
              ],
            },
          };
        },
      }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
      <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    </Stack.Navigator>
  );
};