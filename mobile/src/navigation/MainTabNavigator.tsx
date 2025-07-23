/**
 * Main Tab Navigator
 * 
 * Bottom tab navigation for the main app sections:
 * Home, Browse, Upload, Projects, and Profile.
 */

import React from 'react';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {MainTabParamList, AppState} from '@/types';
import {HomeScreen} from '@/screens/home/HomeScreen';
import {BrowseScreen} from '@/screens/browse/BrowseScreen';
import {UploadTabScreen} from '@/screens/upload/UploadTabScreen';
import {ProjectsScreen} from '@/screens/projects/ProjectsScreen';
import {ProfileScreen} from '@/screens/profile/ProfileScreen';
import {OfflineScreen} from '@/screens/offline/OfflineScreen';
import {colors} from '@/constants/theme';

const Tab = createBottomTabNavigator<MainTabParamList>();

export const MainTabNavigator: React.FC = () => {
  const uploadTasks = useSelector((state: AppState) => state.uploads.tasks);
  const isOnline = useSelector((state: AppState) => state.offline.isOnline);
  const offlineAssetsCount = useSelector((state: AppState) => 
    Object.keys(state.offline.offlineAssets).length
  );
  const unreadNotificationsCount = useSelector((state: AppState) => state.notifications.unreadCount);
  
  const activeUploads = Object.values(uploadTasks).filter(
    task => task.status === 'uploading' || task.status === 'processing'
  );
  const hasActiveUploads = activeUploads.length > 0;

  return (
    <Tab.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.gray500,
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.gray200,
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
        tabBarIconStyle: {
          marginTop: 5,
        },
      }}>
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: 'Home',
          tabBarIcon: ({color, size}) => (
            <Icon name="home" size={size} color={color} />
          ),
        }}
      />
      
      <Tab.Screen
        name="Browse"
        component={BrowseScreen}
        options={{
          title: 'Browse',
          tabBarIcon: ({color, size}) => (
            <Icon name="folder" size={size} color={color} />
          ),
        }}
      />
      
      <Tab.Screen
        name="Upload"
        component={UploadTabScreen}
        options={{
          title: 'Upload',
          tabBarIcon: ({color, size}) => (
            <Icon name="add-circle" size={size} color={color} />
          ),
          tabBarBadge: hasActiveUploads ? activeUploads.length : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.secondary,
            color: colors.onSecondary,
            fontSize: 10,
            minWidth: 16,
            height: 16,
          },
        }}
      />
      
      <Tab.Screen
        name="Projects"
        component={ProjectsScreen}
        options={{
          title: 'Projects',
          tabBarIcon: ({color, size}) => (
            <Icon name="work" size={size} color={color} />
          ),
        }}
      />
      
      <Tab.Screen
        name="Offline"
        component={OfflineScreen}
        options={{
          title: 'Offline',
          tabBarIcon: ({color, size}) => (
            <Icon 
              name={isOnline ? 'cloud-done' : 'cloud-off'} 
              size={size} 
              color={isOnline ? color : colors.warning} 
            />
          ),
          tabBarBadge: offlineAssetsCount > 0 ? offlineAssetsCount : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.success,
            color: colors.onSecondary,
            fontSize: 10,
            minWidth: 16,
            height: 16,
          },
        }}
      />
      
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: 'Profile',
          tabBarIcon: ({color, size}) => (
            <Icon name="person" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};