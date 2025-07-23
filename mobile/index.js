/**
 * MAMS Mobile Application Entry Point
 * 
 * This is the main entry point for the React Native MAMS mobile app.
 * It registers the root component and sets up initial configuration.
 */

import {AppRegistry} from 'react-native';
import App from './src/App';
import {name as appName} from './app.json';

// Register the main component
AppRegistry.registerComponent(appName, () => App);