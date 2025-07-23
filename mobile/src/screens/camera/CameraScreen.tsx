/**
 * Camera Screen
 * 
 * Full-screen camera interface for capturing photos and videos
 * with advanced controls and settings.
 */

import React, {useState, useRef, useEffect} from 'react';
import {
  View,
  StyleSheet,
  StatusBar,
  Alert,
  Dimensions,
  Animated,
  PanResponder,
} from 'react-native';
import {
  Text,
  IconButton,
  Button,
  Surface,
  Portal,
  Modal,
  Switch,
  List,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch} from 'react-redux';
import {RNCamera} from 'react-native-camera';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import RNFS from 'react-native-fs';

import {colors, spacing, typography} from '@/constants/theme';
import {addUploadTask} from '@/store/slices/uploadsSlice';
import {uploadService} from '@/services/uploadService';

const {width: screenWidth, height: screenHeight} = Dimensions.get('window');

interface CameraSettings {
  flashMode: 'off' | 'on' | 'auto' | 'torch';
  cameraType: 'front' | 'back';
  captureQuality: 'low' | 'medium' | 'high';
  videoQuality: '480p' | '720p' | '1080p' | '4K';
  focusMode: 'on' | 'off' | 'auto';
  whiteBalance: 'auto' | 'sunny' | 'cloudy' | 'shadow' | 'incandescent' | 'fluorescent';
  iso: 'auto' | number;
  exposure: number;
}

export const CameraScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const cameraRef = useRef<RNCamera>(null);

  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [captureMode, setCaptureMode] = useState<'photo' | 'video'>('photo');
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const [settings, setSettings] = useState<CameraSettings>({
    flashMode: 'off',
    cameraType: 'back',
    captureQuality: 'high',
    videoQuality: '1080p',
    focusMode: 'auto',
    whiteBalance: 'auto',
    iso: 'auto',
    exposure: 0,
  });

  // Animated values for UI
  const recordingAnimation = useRef(new Animated.Value(1)).current;
  const zoomValue = useRef(new Animated.Value(1)).current;
  const exposureSlide = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    checkCameraPermissions();
  }, []);

  useEffect(() => {
    if (isRecording) {
      startRecordingAnimation();
    } else {
      stopRecordingAnimation();
    }
  }, [isRecording]);

  const checkCameraPermissions = async () => {
    try {
      const cameraPermission = await check(PERMISSIONS.IOS.CAMERA);
      const micPermission = await check(PERMISSIONS.IOS.MICROPHONE);

      if (cameraPermission === RESULTS.GRANTED && micPermission === RESULTS.GRANTED) {
        setHasPermission(true);
      } else {
        requestPermissions();
      }
    } catch (error) {
      console.error('Permission check failed:', error);
      setHasPermission(false);
    }
  };

  const requestPermissions = async () => {
    try {
      const cameraResult = await request(PERMISSIONS.IOS.CAMERA);
      const micResult = await request(PERMISSIONS.IOS.MICROPHONE);

      setHasPermission(
        cameraResult === RESULTS.GRANTED && micResult === RESULTS.GRANTED
      );
    } catch (error) {
      console.error('Permission request failed:', error);
      setHasPermission(false);
    }
  };

  const startRecordingAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(recordingAnimation, {
          toValue: 0.3,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(recordingAnimation, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const stopRecordingAnimation = () => {
    recordingAnimation.stopAnimation();
    Animated.timing(recordingAnimation, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
  };

  const handleCapture = async () => {
    if (!cameraRef.current || isProcessing) return;

    setIsProcessing(true);

    try {
      if (captureMode === 'photo') {
        await capturePhoto();
      } else {
        if (isRecording) {
          await stopVideoRecording();
        } else {
          await startVideoRecording();
        }
      }
    } catch (error) {
      console.error('Capture failed:', error);
      Alert.alert('Error', 'Failed to capture media. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const capturePhoto = async () => {
    if (!cameraRef.current) return;

    const options = {
      quality: settings.captureQuality === 'high' ? 1 : settings.captureQuality === 'medium' ? 0.7 : 0.5,
      base64: false,
      pauseAfterCapture: true,
      fixOrientation: true,
    };

    const data = await cameraRef.current.takePictureAsync(options);
    await processMediaFile(data.uri, 'photo');
  };

  const startVideoRecording = async () => {
    if (!cameraRef.current) return;

    const options = {
      quality: settings.videoQuality,
      maxDuration: 300, // 5 minutes max
      mute: false,
    };

    setIsRecording(true);
    const data = await cameraRef.current.recordAsync(options);
    await processMediaFile(data.uri, 'video');
  };

  const stopVideoRecording = async () => {
    if (!cameraRef.current) return;

    cameraRef.current.stopRecording();
    setIsRecording(false);
  };

  const processMediaFile = async (uri: string, type: 'photo' | 'video') => {
    try {
      // Get file info
      const fileInfo = await RNFS.stat(uri);
      const fileName = `${type}_${Date.now()}.${type === 'photo' ? 'jpg' : 'mp4'}`;
      const fileType = type === 'photo' ? 'image/jpeg' : 'video/mp4';

      // Create upload task
      const uploadTask = await uploadService.createUploadTask({
        uri,
        name: fileName,
        type: fileType,
        size: fileInfo.size,
      });

      // Add metadata
      uploadTask.metadata = {
        captured_with: 'mobile_camera',
        camera_settings: settings,
        capture_timestamp: new Date().toISOString(),
        file_type: type,
      };

      // Add to upload queue
      dispatch(addUploadTask(uploadTask));

      Alert.alert(
        'Captured!',
        `${type === 'photo' ? 'Photo' : 'Video'} captured and added to upload queue.`,
        [
          {text: 'Capture More', style: 'default'},
          {
            text: 'View Uploads',
            onPress: () => navigation.navigate('Upload' as never),
          },
        ]
      );
    } catch (error) {
      console.error('Failed to process media file:', error);
      Alert.alert('Error', 'Failed to process captured media.');
    }
  };

  const handleSettingChange = (key: keyof CameraSettings, value: any) => {
    setSettings(prev => ({...prev, [key]: value}));
  };

  const toggleFlash = () => {
    const flashModes: Array<CameraSettings['flashMode']> = ['off', 'on', 'auto'];
    const currentIndex = flashModes.indexOf(settings.flashMode);
    const nextIndex = (currentIndex + 1) % flashModes.length;
    handleSettingChange('flashMode', flashModes[nextIndex]);
  };

  const toggleCamera = () => {
    handleSettingChange('cameraType', settings.cameraType === 'back' ? 'front' : 'back');
  };

  const getFlashIcon = () => {
    switch (settings.flashMode) {
      case 'on':
        return 'flash-on';
      case 'auto':
        return 'flash-auto';
      default:
        return 'flash-off';
    }
  };

  // Pan responder for zoom and exposure
  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: () => true,
      onPanResponderMove: (event, gestureState) => {
        const {dy} = gestureState;
        const newExposure = Math.max(-2, Math.min(2, settings.exposure - dy / 100));
        handleSettingChange('exposure', newExposure);
        
        Animated.setValue(exposureSlide, newExposure / 2);
      },
    })
  ).current;

  const renderCameraSettings = () => (
    <Portal>
      <Modal
        visible={settingsVisible}
        onDismiss={() => setSettingsVisible(false)}
        contentContainerStyle={styles.settingsModal}>
        
        <Text style={styles.settingsTitle}>Camera Settings</Text>
        
        <List.Item
          title="Capture Quality"
          description={settings.captureQuality}
          right={() => (
            <Button
              mode="outlined"
              onPress={() => {
                const qualities: Array<CameraSettings['captureQuality']> = ['low', 'medium', 'high'];
                const currentIndex = qualities.indexOf(settings.captureQuality);
                const nextIndex = (currentIndex + 1) % qualities.length;
                handleSettingChange('captureQuality', qualities[nextIndex]);
              }}>
              {settings.captureQuality.toUpperCase()}
            </Button>
          )}
        />
        
        <List.Item
          title="Video Quality"
          description={settings.videoQuality}
          right={() => (
            <Button
              mode="outlined"
              onPress={() => {
                const qualities: Array<CameraSettings['videoQuality']> = ['480p', '720p', '1080p', '4K'];
                const currentIndex = qualities.indexOf(settings.videoQuality);
                const nextIndex = (currentIndex + 1) % qualities.length;
                handleSettingChange('videoQuality', qualities[nextIndex]);
              }}>
              {settings.videoQuality}
            </Button>
          )}
        />
        
        <List.Item
          title="White Balance"
          description={settings.whiteBalance}
          right={() => (
            <Button
              mode="outlined"
              onPress={() => {
                const modes: Array<CameraSettings['whiteBalance']> = ['auto', 'sunny', 'cloudy', 'shadow'];
                const currentIndex = modes.indexOf(settings.whiteBalance);
                const nextIndex = (currentIndex + 1) % modes.length;
                handleSettingChange('whiteBalance', modes[nextIndex]);
              }}>
              {settings.whiteBalance.toUpperCase()}
            </Button>
          )}
        />
        
        <Button
          mode="contained"
          onPress={() => setSettingsVisible(false)}
          style={styles.closeButton}>
          Close
        </Button>
      </Modal>
    </Portal>
  );

  if (hasPermission === null) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Checking camera permissions...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionTitle}>Camera Access Required</Text>
        <Text style={styles.permissionText}>
          Please grant camera and microphone permissions to capture photos and videos.
        </Text>
        <Button mode="contained" onPress={requestPermissions}>
          Grant Permissions
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar hidden />
      
      <RNCamera
        ref={cameraRef}
        style={styles.camera}
        type={settings.cameraType === 'back' ? RNCamera.Constants.Type.back : RNCamera.Constants.Type.front}
        flashMode={settings.flashMode === 'off' ? RNCamera.Constants.FlashMode.off :
                  settings.flashMode === 'on' ? RNCamera.Constants.FlashMode.on :
                  settings.flashMode === 'auto' ? RNCamera.Constants.FlashMode.auto :
                  RNCamera.Constants.FlashMode.torch}
        autoFocus={settings.focusMode === 'auto' ? RNCamera.Constants.AutoFocus.on : RNCamera.Constants.AutoFocus.off}
        whiteBalance={RNCamera.Constants.WhiteBalance[settings.whiteBalance]}
        exposure={settings.exposure}
        captureAudio={true}
        {...panResponder.panHandlers}
      />

      {/* Top Controls */}
      <Surface style={styles.topControls}>
        <IconButton
          icon="close"
          iconColor={colors.onSurface}
          size={24}
          onPress={() => navigation.goBack()}
        />
        
        <View style={styles.topRightControls}>
          <IconButton
            icon={getFlashIcon()}
            iconColor={colors.onSurface}
            size={24}
            onPress={toggleFlash}
          />
          
          <IconButton
            icon="settings"
            iconColor={colors.onSurface}
            size={24}
            onPress={() => setSettingsVisible(true)}
          />
        </View>
      </Surface>

      {/* Mode Selector */}
      <Surface style={styles.modeSelector}>
        <Button
          mode={captureMode === 'photo' ? 'contained' : 'outlined'}
          onPress={() => setCaptureMode('photo')}
          style={styles.modeButton}>
          Photo
        </Button>
        
        <Button
          mode={captureMode === 'video' ? 'contained' : 'outlined'}
          onPress={() => setCaptureMode('video')}
          style={styles.modeButton}>
          Video
        </Button>
      </Surface>

      {/* Bottom Controls */}
      <Surface style={styles.bottomControls}>
        <View style={styles.captureControls}>
          <IconButton
            icon="flip-camera-ios"
            iconColor={colors.onSurface}
            size={32}
            onPress={toggleCamera}
          />
          
          <Animated.View
            style={[
              styles.captureButton,
              {
                opacity: recordingAnimation,
                backgroundColor: isRecording ? colors.error : colors.primary,
              },
            ]}>
            <IconButton
              icon={captureMode === 'photo' ? 'camera' : isRecording ? 'stop' : 'videocam'}
              iconColor={colors.onPrimary}
              size={32}
              onPress={handleCapture}
              disabled={isProcessing}
            />
          </Animated.View>
          
          <IconButton
            icon="photo-library"
            iconColor={colors.onSurface}
            size={32}
            onPress={() => navigation.navigate('Browse' as never)}
          />
        </View>
        
        {isRecording && (
          <Text style={styles.recordingText}>Recording...</Text>
        )}
      </Surface>

      {renderCameraSettings()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.black,
  },
  camera: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
    backgroundColor: colors.background,
  },
  permissionTitle: {
    ...typography.headlineMedium,
    color: colors.onSurface,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  permissionText: {
    ...typography.bodyLarge,
    color: colors.gray600,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  topControls: {
    position: 'absolute',
    top: 50,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  topRightControls: {
    flexDirection: 'row',
  },
  modeSelector: {
    position: 'absolute',
    top: screenHeight * 0.15,
    left: screenWidth * 0.3,
    right: screenWidth * 0.3,
    flexDirection: 'row',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 25,
    padding: spacing.xs,
  },
  modeButton: {
    flex: 1,
    marginHorizontal: spacing.xs,
  },
  bottomControls: {
    position: 'absolute',
    bottom: 50,
    left: 0,
    right: 0,
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
    paddingVertical: spacing.lg,
  },
  captureControls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: screenWidth * 0.8,
  },
  captureButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
  },
  recordingText: {
    ...typography.bodyLarge,
    color: colors.error,
    fontWeight: '600',
    marginTop: spacing.sm,
  },
  settingsModal: {
    backgroundColor: colors.surface,
    margin: spacing.lg,
    borderRadius: 8,
    padding: spacing.lg,
  },
  settingsTitle: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  closeButton: {
    marginTop: spacing.lg,
  },
});