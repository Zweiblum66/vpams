/**
 * AR Preview Screen
 * 
 * Augmented reality preview screen for viewing assets
 * in AR space using ARKit/ARCore.
 */

import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  StyleSheet,
  Alert,
  TouchableOpacity,
  Animated,
  Platform,
} from 'react-native';
import {
  Appbar,
  FAB,
  Text,
  Portal,
  Modal,
  List,
  IconButton,
  Chip,
  Snackbar,
} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {Canvas} from '@react-three/fiber/native';
import {OrbitControls, Box, Plane, Text as Text3D} from '@react-three/drei/native';
import * as THREE from 'three';

import {AppState, Asset} from '@/types';
import {arService, ARPreviewType, ARConfiguration} from '@/services/arService';
import {colors, spacing, typography} from '@/constants/theme';
import {shareService} from '@/services/shareService';

type ARPreviewScreenRouteProp = RouteProp<{
  ARPreview: {assetId: string; previewType?: ARPreviewType};
}, 'ARPreview'>;

export const ARPreviewScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<ARPreviewScreenRouteProp>();
  const {assetId, previewType} = route.params;

  const asset = useSelector((state: AppState) => 
    state.assets.assets.find(a => a.id === assetId)
  );

  const [isARSupported, setIsARSupported] = useState(false);
  const [arSession, setArSession] = useState<any>(null);
  const [isPlacing, setIsPlacing] = useState(true);
  const [placementHints, setPlacementHints] = useState<string[]>([]);
  const [showControls, setShowControls] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [configuration, setConfiguration] = useState<ARConfiguration>({
    scale: 1.0,
    position: {x: 0, y: 0, z: -2},
    rotation: {x: 0, y: 0, z: 0},
    lighting: true,
    shadows: true,
    occlusion: true,
    autoPlace: true,
  });

  const scaleAnimation = useRef(new Animated.Value(1)).current;
  const hintOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    checkARSupport();
    if (asset) {
      startARSession();
    }

    // Animate hints
    Animated.loop(
      Animated.sequence([
        Animated.timing(hintOpacity, {
          toValue: 0.3,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(hintOpacity, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    return () => {
      arService.endSession();
    };
  }, []);

  const checkARSupport = async () => {
    try {
      const capabilities = await arService.checkARSupport();
      setIsARSupported(capabilities.isSupported);
      
      if (!capabilities.isSupported) {
        Alert.alert(
          'AR Not Supported',
          'Your device does not support AR features. You need a device with ARKit (iOS) or ARCore (Android) support.',
          [{text: 'OK', onPress: () => navigation.goBack()}]
        );
      }
    } catch (error) {
      console.error('Failed to check AR support:', error);
    }
  };

  const startARSession = async () => {
    if (!asset) return;

    try {
      const session = await arService.startARSession(asset, previewType);
      setArSession(session);
      setConfiguration(session.configuration);
      
      const hints = arService.getPlacementHints(session.type);
      setPlacementHints(hints);
    } catch (error) {
      console.error('Failed to start AR session:', error);
      Alert.alert('Error', 'Failed to start AR preview');
    }
  };

  const handlePlaceAsset = async () => {
    if (!asset) return;

    try {
      await arService.placeAsset(
        asset.id,
        configuration.position,
        configuration.rotation,
        configuration.scale
      );
      
      setIsPlacing(false);
      setSnackbarMessage('Asset placed successfully');
      
      // Animate placement
      Animated.sequence([
        Animated.timing(scaleAnimation, {
          toValue: 1.2,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(scaleAnimation, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    } catch (error) {
      console.error('Failed to place asset:', error);
    }
  };

  const handleTakeScreenshot = async () => {
    try {
      const screenshot = await arService.takeARScreenshot();
      setSnackbarMessage('Screenshot saved');
      
      // Optionally share
      Alert.alert(
        'Screenshot Saved',
        'Would you like to share the AR screenshot?',
        [
          {text: 'Cancel', style: 'cancel'},
          {
            text: 'Share',
            onPress: () => handleShare(screenshot),
          },
        ]
      );
    } catch (error) {
      console.error('Failed to take screenshot:', error);
    }
  };

  const handleShare = async (screenshot?: string) => {
    if (!asset) return;

    try {
      const placements = arService.getAllPlacements();
      const placement = placements.find(p => p.assetId === asset.id);
      
      if (placement && screenshot) {
        placement.screenshot = screenshot;
      }

      await shareService.shareAsset(asset, {
        includeAR: true,
        arScreenshot: screenshot,
      });
    } catch (error) {
      console.error('Failed to share:', error);
    }
  };

  const updateConfiguration = (updates: Partial<ARConfiguration>) => {
    const newConfig = arService.updateConfiguration(updates);
    if (newConfig) {
      setConfiguration(newConfig);
    }
  };

  const renderARContent = () => {
    if (!asset || !arSession) return null;

    switch (arSession.type) {
      case 'image_on_wall':
        return (
          <group position={[configuration.position.x, configuration.position.y, configuration.position.z]}>
            <Box args={[2, 2, 0.1]} scale={configuration.scale}>
              <meshStandardMaterial color="white" />
            </Box>
            <Text3D
              position={[0, -1.5, 0]}
              fontSize={0.3}
              color={colors.primary}>
              {asset.name}
            </Text3D>
          </group>
        );

      case 'video_screen':
        return (
          <group position={[configuration.position.x, configuration.position.y, configuration.position.z]}>
            <Box args={[3.2, 1.8, 0.1]} scale={configuration.scale}>
              <meshStandardMaterial color="black" />
            </Box>
            <Plane args={[3, 1.7]} position={[0, 0, 0.06]}>
              <meshBasicMaterial color={colors.primary} />
            </Plane>
          </group>
        );

      case '3d_model':
        return (
          <Box 
            args={[1, 1, 1]} 
            position={[configuration.position.x, configuration.position.y, configuration.position.z]}
            scale={configuration.scale}>
            <meshStandardMaterial color={colors.secondary} />
          </Box>
        );

      default:
        return null;
    }
  };

  const renderControlPanel = () => (
    <Portal>
      <Modal
        visible={showControls}
        onDismiss={() => setShowControls(false)}
        contentContainerStyle={styles.controlsModal}>
        
        <Text style={styles.controlsTitle}>AR Controls</Text>

        <List.Section>
          <List.Item
            title="Scale"
            description={`${(configuration.scale * 100).toFixed(0)}%`}
            left={(props) => <List.Icon {...props} icon="resize" />}
            right={() => (
              <View style={styles.sliderContainer}>
                <IconButton
                  icon="minus"
                  size={20}
                  onPress={() => updateConfiguration({
                    scale: Math.max(0.1, configuration.scale - 0.1)
                  })}
                />
                <Text>{configuration.scale.toFixed(1)}</Text>
                <IconButton
                  icon="plus"
                  size={20}
                  onPress={() => updateConfiguration({
                    scale: Math.min(5, configuration.scale + 0.1)
                  })}
                />
              </View>
            )}
          />

          <List.Item
            title="Lighting"
            description="Realistic lighting effects"
            left={(props) => <List.Icon {...props} icon="lightbulb" />}
            right={() => (
              <IconButton
                icon={configuration.lighting ? 'toggle-on' : 'toggle-off'}
                size={30}
                onPress={() => updateConfiguration({
                  lighting: !configuration.lighting
                })}
              />
            )}
          />

          <List.Item
            title="Shadows"
            description="Cast shadows on surfaces"
            left={(props) => <List.Icon {...props} icon="blur-on" />}
            right={() => (
              <IconButton
                icon={configuration.shadows ? 'toggle-on' : 'toggle-off'}
                size={30}
                onPress={() => updateConfiguration({
                  shadows: !configuration.shadows
                })}
              />
            )}
          />

          <List.Item
            title="Occlusion"
            description="Hide behind real objects"
            left={(props) => <List.Icon {...props} icon="layers" />}
            right={() => (
              <IconButton
                icon={configuration.occlusion ? 'toggle-on' : 'toggle-off'}
                size={30}
                onPress={() => updateConfiguration({
                  occlusion: !configuration.occlusion
                })}
              />
            )}
          />
        </List.Section>

        <View style={styles.controlsActions}>
          <Chip 
            mode="outlined"
            onPress={() => {
              setConfiguration({
                ...configuration,
                scale: 1.0,
                position: {x: 0, y: 0, z: -2},
                rotation: {x: 0, y: 0, z: 0},
              });
              setShowControls(false);
            }}>
            Reset
          </Chip>
        </View>
      </Modal>
    </Portal>
  );

  if (!asset || !isARSupported) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="AR Preview" subtitle={asset.name} />
        <Appbar.Action icon="tune" onPress={() => setShowControls(true)} />
        <Appbar.Action icon="share" onPress={() => handleShare()} />
      </Appbar.Header>

      <View style={styles.arContainer}>
        <Canvas
          camera={{position: [0, 0, 5], fov: 75}}
          style={styles.canvas}
          gl={{antialias: true, alpha: true}}>
          
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} castShadow={configuration.shadows} />
          
          {renderARContent()}
          
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
          />
        </Canvas>

        {/* Placement hints */}
        {isPlacing && placementHints.length > 0 && (
          <Animated.View 
            style={[styles.hintsContainer, {opacity: hintOpacity}]}>
            <Text style={styles.hintText}>
              {placementHints[0]}
            </Text>
          </Animated.View>
        )}

        {/* AR Grid indicator */}
        {isPlacing && (
          <View style={styles.gridOverlay} pointerEvents="none">
            <Icon name="grid-on" size={200} color={`${colors.primary}20`} />
          </View>
        )}
      </View>

      {/* Action buttons */}
      <FAB.Group
        open={false}
        visible={true}
        icon="layers"
        actions={[
          {
            icon: 'camera',
            label: 'Screenshot',
            onPress: handleTakeScreenshot,
          },
          {
            icon: isPlacing ? 'check' : 'edit',
            label: isPlacing ? 'Place Here' : 'Reposition',
            onPress: isPlacing ? handlePlaceAsset : () => setIsPlacing(true),
          },
          {
            icon: 'tune',
            label: 'Controls',
            onPress: () => setShowControls(true),
          },
        ]}
        onStateChange={() => {}}
        style={styles.fabGroup}
      />

      {renderControlPanel()}

      <Snackbar
        visible={!!snackbarMessage}
        onDismiss={() => setSnackbarMessage('')}
        duration={3000}
        action={{
          label: 'OK',
          onPress: () => setSnackbarMessage(''),
        }}>
        {snackbarMessage}
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.black,
  },
  appBar: {
    backgroundColor: colors.black,
    elevation: 0,
  },
  arContainer: {
    flex: 1,
    position: 'relative',
  },
  canvas: {
    flex: 1,
  },
  hintsContainer: {
    position: 'absolute',
    top: spacing.xl,
    left: spacing.md,
    right: spacing.md,
    backgroundColor: `${colors.black}CC`,
    padding: spacing.md,
    borderRadius: 8,
    alignItems: 'center',
  },
  hintText: {
    ...typography.bodyLarge,
    color: colors.white,
    textAlign: 'center',
  },
  gridOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  fabGroup: {
    paddingBottom: spacing.md,
  },
  controlsModal: {
    backgroundColor: colors.surface,
    margin: spacing.lg,
    padding: spacing.lg,
    borderRadius: 8,
    maxHeight: '80%',
  },
  controlsTitle: {
    ...typography.titleLarge,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    minWidth: 120,
  },
  controlsActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: spacing.lg,
  },
});