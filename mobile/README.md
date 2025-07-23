# MAMS Mobile Application

A React Native mobile application for the Digital Media Asset Management System (MAMS), providing native iOS and Android access to media assets, projects, and workflows.

## Features

### Core Functionality
- **Asset Browsing**: Browse and search media assets with advanced filters
- **Asset Viewing**: Full-screen media viewer supporting images, videos, audio, and documents
- **Upload Management**: Camera capture and file upload with progress tracking
- **Project Management**: Access and manage projects and their assets
- **Offline Support**: Download assets for offline viewing and sync when connected

### Authentication
- Username/password authentication
- Biometric authentication (fingerprint/Face ID)
- Secure token storage with auto-refresh
- Remember login functionality

### Media Support
- **Images**: JPEG, PNG, WebP, TIFF, BMP
- **Videos**: MP4, MOV, AVI, MKV with proxy streaming
- **Audio**: MP3, WAV, AAC, FLAC with waveform visualization
- **Documents**: PDF viewing with text search

### Advanced Features
- Real-time upload progress with pause/resume
- Chunked uploads for large files
- Automatic thumbnail and proxy generation
- Search with natural language processing
- Push notifications for workflow updates
- Dark/light theme support

## Architecture

### Technology Stack
- **Framework**: React Native 0.72.4
- **Navigation**: React Navigation 6.x
- **State Management**: Redux Toolkit with RTK Query
- **Persistence**: Redux Persist with AsyncStorage
- **UI Components**: React Native Paper (Material Design)
- **Media Handling**: React Native Video, Image Picker
- **Security**: React Native Keychain, Biometrics

### Project Structure
```
src/
├── components/          # Reusable UI components
├── screens/            # Screen components organized by feature
│   ├── auth/           # Authentication screens
│   ├── home/           # Dashboard and home screen
│   ├── browse/         # Asset browsing and search
│   ├── upload/         # Upload and camera screens
│   ├── projects/       # Project management
│   ├── assets/         # Asset detail and viewer
│   ├── settings/       # App settings and profile
│   └── search/         # Search and filters
├── navigation/         # Navigation configuration
├── store/             # Redux store and slices
│   ├── slices/        # Feature-specific state slices
│   └── api/           # RTK Query API endpoints
├── services/          # Business logic and API clients
├── hooks/             # Custom React hooks
├── utils/             # Utility functions
├── types/             # TypeScript type definitions
├── constants/         # Theme, colors, and constants
└── assets/            # Images, icons, and static files
```

### State Management
The app uses Redux Toolkit for state management with the following slices:

- **auth**: User authentication and session management
- **assets**: Asset cache and metadata
- **projects**: Project data and memberships
- **uploads**: Upload queue and progress tracking
- **search**: Search state and history
- **settings**: User preferences and app configuration
- **offline**: Offline state and sync management

## Getting Started

### Prerequisites
- Node.js 18+ and npm 8+
- React Native CLI
- iOS: Xcode 14+ and iOS Simulator
- Android: Android Studio with SDK 31+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MyVideoMAM/mobile
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **iOS Setup**
   ```bash
   cd ios && pod install && cd ..
   ```

4. **Android Setup**
   - Open `android/` folder in Android Studio
   - Sync project with Gradle files
   - Ensure SDK 31+ is installed

### Configuration

1. **Environment Variables**
   Create `.env` file in the mobile directory:
   ```env
   API_BASE_URL=http://localhost:8000
   API_TIMEOUT=30000
   UPLOAD_CHUNK_SIZE=1048576
   MAX_CONCURRENT_UPLOADS=3
   SENTRY_DSN=your_sentry_dsn_here
   ```

2. **API Configuration**
   Update `src/constants/config.ts` with your MAMS API endpoints:
   ```typescript
   export const API_CONFIG = {
     BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
     ENDPOINTS: {
       AUTH: '/api/v1/auth',
       ASSETS: '/api/v1/assets',
       PROJECTS: '/api/v1/projects',
       UPLOAD: '/api/v1/upload',
       SEARCH: '/api/v1/search',
     },
   };
   ```

### Running the App

1. **Start Metro Bundler**
   ```bash
   npm start
   ```

2. **Run on iOS**
   ```bash
   npm run ios
   ```

3. **Run on Android**
   ```bash
   npm run android
   ```

### Development

1. **Enable Hot Reload**
   - Shake device or press Cmd+D (iOS) / Cmd+M (Android)
   - Enable "Fast Refresh"

2. **Debugging**
   - Use React Native Debugger
   - Enable network inspector for API calls
   - Use Flipper for advanced debugging

3. **Testing**
   ```bash
   npm test              # Run unit tests
   npm run test:watch    # Watch mode
   npm run test:coverage # Coverage report
   ```

## API Integration

### Authentication
The app integrates with MAMS authentication APIs:

```typescript
// Login
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "password",
  "remember_me": true
}

// Response
{
  "user": { ... },
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": "..."
  }
}
```

### Asset Management
```typescript
// Get assets
GET /api/v1/assets?page=1&limit=20&project_id=123

// Upload asset
POST /api/v1/assets/upload
Content-Type: multipart/form-data

// Get asset details
GET /api/v1/assets/:id

// Download asset
GET /api/v1/assets/:id/download?quality=original
```

### Real-time Updates
The app supports WebSocket connections for real-time updates:

```typescript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

// Listen for upload progress
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'upload_progress') {
    dispatch(updateUploadProgress(data));
  }
};
```

## Build and Deployment

### iOS Build
1. **Debug Build**
   ```bash
   npm run build:ios-debug
   ```

2. **Release Build**
   ```bash
   npm run build:ios-release
   ```

3. **App Store Submission**
   - Update version in `ios/MAMSMobile/Info.plist`
   - Archive in Xcode
   - Upload to App Store Connect

### Android Build
1. **Debug APK**
   ```bash
   npm run build:android-debug
   ```

2. **Release APK**
   ```bash
   npm run build:android-release
   ```

3. **Google Play Submission**
   - Update version in `android/app/build.gradle`
   - Generate signed APK/AAB
   - Upload to Google Play Console

## Security Considerations

### Data Protection
- All API communications use HTTPS
- Sensitive data stored in device keychain
- Biometric authentication for app access
- Automatic token refresh and rotation

### File Security
- Downloaded files encrypted at rest
- Secure file sharing with other apps
- Automatic cache cleanup
- Watermarking for sensitive content

### Privacy
- No analytics without user consent
- Location data only with permission
- Camera/microphone access on demand
- GDPR compliance for EU users

## Performance Optimization

### Bundle Size
- Code splitting for screens
- Tree shaking for unused code
- Image optimization and compression
- Dynamic imports for heavy libraries

### Memory Management
- Lazy loading of large assets
- Image cache with size limits
- Background task management
- Memory leak detection

### Network Efficiency
- Request batching and caching
- Optimistic updates for better UX
- Progressive image loading
- Bandwidth-aware quality selection

## Troubleshooting

### Common Issues

1. **Metro bundler issues**
   ```bash
   npm run clean
   npm start --reset-cache
   ```

2. **iOS build fails**
   ```bash
   cd ios
   pod deintegrate
   pod install
   ```

3. **Android build fails**
   ```bash
   cd android
   ./gradlew clean
   ```

4. **Network requests failing**
   - Check API_BASE_URL in .env
   - Verify MAMS backend is running
   - Check device network connectivity

### Debug Tools
- React Native Debugger
- Flipper for network inspection
- Xcode Instruments for iOS profiling
- Android Studio Profiler

## Contributing

1. Follow React Native and TypeScript best practices
2. Use ESLint and Prettier for code formatting
3. Write unit tests for business logic
4. Update documentation for new features
5. Test on both iOS and Android devices

## License

This project is part of the MAMS platform and follows the same licensing terms.