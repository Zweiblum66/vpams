/**
 * Main Application Stack Navigator
 * 
 * Contains the main app navigation including tab navigator
 * and modal screens for asset details, upload, etc.
 */

import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';

import {RootStackParamList} from '@/types';
import {MainTabNavigator} from './MainTabNavigator';
import {AssetDetailScreen} from '@/screens/assets/AssetDetailScreen';
import {AssetViewerScreen} from '@/screens/assets/AssetViewerScreen';
import {AssetEditorScreen} from '@/screens/assets/AssetEditorScreen';
import {ProjectDetailScreen} from '@/screens/projects/ProjectDetailScreen';
import {ProjectAssetsScreen} from '@/screens/projects/ProjectAssetsScreen';
import {UploadScreen} from '@/screens/upload/UploadScreen';
import {CameraCaptureScreen} from '@/screens/upload/CameraCaptureScreen';
import {SearchScreen} from '@/screens/search/SearchScreen';
import {SearchFiltersScreen} from '@/screens/search/SearchFiltersScreen';
import {SettingsScreen} from '@/screens/settings/SettingsScreen';
import {ProfileScreen} from '@/screens/settings/ProfileScreen';
import {DownloadSettingsScreen} from '@/screens/settings/DownloadSettingsScreen';

const Stack = createStackNavigator<RootStackParamList>();

export const MainStack: React.FC = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        gestureEnabled: true,
        presentation: 'card',
      }}>
      {/* Main tab navigator */}
      <Stack.Screen name="MainTabs" component={MainTabNavigator} />
      
      {/* Asset screens */}
      <Stack.Group
        screenOptions={{
          presentation: 'modal',
          gestureEnabled: true,
          headerShown: true,
          headerStyle: {
            backgroundColor: '#1976D2',
          },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: {
            fontWeight: '600',
          },
        }}>
        <Stack.Screen 
          name="AssetDetail" 
          component={AssetDetailScreen}
          options={{title: 'Asset Details'}}
        />
        <Stack.Screen 
          name="AssetViewer" 
          component={AssetViewerScreen}
          options={{
            title: 'Asset Viewer',
            headerStyle: {
              backgroundColor: '#000000',
            },
          }}
        />
        <Stack.Screen 
          name="AssetEditor" 
          component={AssetEditorScreen}
          options={{title: 'Edit Asset'}}
        />
      </Stack.Group>
      
      {/* Project screens */}
      <Stack.Group
        screenOptions={{
          presentation: 'card',
          headerShown: true,
          headerStyle: {
            backgroundColor: '#1976D2',
          },
          headerTintColor: '#FFFFFF',
        }}>
        <Stack.Screen 
          name="ProjectDetail" 
          component={ProjectDetailScreen}
          options={{title: 'Project Details'}}
        />
        <Stack.Screen 
          name="ProjectAssets" 
          component={ProjectAssetsScreen}
          options={{title: 'Project Assets'}}
        />
      </Stack.Group>
      
      {/* Upload screens */}
      <Stack.Group
        screenOptions={{
          presentation: 'modal',
          headerShown: true,
          headerStyle: {
            backgroundColor: '#1976D2',
          },
          headerTintColor: '#FFFFFF',
        }}>
        <Stack.Screen 
          name="Upload" 
          component={UploadScreen}
          options={{title: 'Upload Assets'}}
        />
        <Stack.Screen 
          name="CameraCapture" 
          component={CameraCaptureScreen}
          options={{
            title: 'Camera',
            headerStyle: {
              backgroundColor: '#000000',
            },
          }}
        />
      </Stack.Group>
      
      {/* Search screens */}
      <Stack.Group
        screenOptions={{
          presentation: 'card',
          headerShown: true,
          headerStyle: {
            backgroundColor: '#1976D2',
          },
          headerTintColor: '#FFFFFF',
        }}>
        <Stack.Screen 
          name="Search" 
          component={SearchScreen}
          options={{title: 'Search Assets'}}
        />
        <Stack.Screen 
          name="SearchFilters" 
          component={SearchFiltersScreen}
          options={{title: 'Search Filters'}}
        />
      </Stack.Group>
      
      {/* Settings screens */}
      <Stack.Group
        screenOptions={{
          presentation: 'card',
          headerShown: true,
          headerStyle: {
            backgroundColor: '#1976D2',
          },
          headerTintColor: '#FFFFFF',
        }}>
        <Stack.Screen 
          name="Settings" 
          component={SettingsScreen}
          options={{title: 'Settings'}}
        />
        <Stack.Screen 
          name="Profile" 
          component={ProfileScreen}
          options={{title: 'Profile'}}
        />
        <Stack.Screen 
          name="DownloadSettings" 
          component={DownloadSettingsScreen}
          options={{title: 'Download Settings'}}
        />
      </Stack.Group>
    </Stack.Navigator>
  );
};