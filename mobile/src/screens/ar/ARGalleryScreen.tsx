/**
 * AR Gallery Screen
 * 
 * Virtual gallery experience for viewing multiple
 * assets in an AR environment.
 */

import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  Dimensions,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  Chip,
  FAB,
  Portal,
  Dialog,
  List,
  Button,
  IconButton,
  ProgressBar,
} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {Canvas} from '@react-three/fiber/native';
import {Environment, PerspectiveCamera} from '@react-three/drei/native';

import {AppState, Asset, Project} from '@/types';
import {arService} from '@/services/arService';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth} = Dimensions.get('window');

type ARGalleryScreenRouteProp = RouteProp<{
  ARGallery: {initialAssetId?: string; projectId?: string};
}, 'ARGallery'>;

interface GalleryAsset {
  asset: Asset;
  position: {x: number; y: number; z: number};
  rotation: {x: number; y: number; z: number};
  scale: number;
}

interface GalleryLayout {
  name: string;
  icon: string;
  positions: Array<{x: number; y: number; z: number}>;
}

const GALLERY_LAYOUTS: GalleryLayout[] = [
  {
    name: 'Linear',
    icon: 'view-column',
    positions: [
      {x: -2, y: 0, z: -3},
      {x: 0, y: 0, z: -3},
      {x: 2, y: 0, z: -3},
      {x: 4, y: 0, z: -3},
    ],
  },
  {
    name: 'Grid',
    icon: 'grid-view',
    positions: [
      {x: -1.5, y: 1, z: -3},
      {x: 1.5, y: 1, z: -3},
      {x: -1.5, y: -1, z: -3},
      {x: 1.5, y: -1, z: -3},
    ],
  },
  {
    name: 'Circular',
    icon: 'panorama-fish-eye',
    positions: [
      {x: 0, y: 0, z: -3},
      {x: 2, y: 0, z: -2},
      {x: 2, y: 0, z: 0},
      {x: 0, y: 0, z: 1},
      {x: -2, y: 0, z: 0},
      {x: -2, y: 0, z: -2},
    ],
  },
  {
    name: 'Museum',
    icon: 'museum',
    positions: [
      {x: -3, y: 0, z: -4},
      {x: 0, y: 0, z: -4},
      {x: 3, y: 0, z: -4},
      {x: -3, y: 0, z: 0},
      {x: 3, y: 0, z: 0},
      {x: -3, y: 0, z: 4},
      {x: 0, y: 0, z: 4},
      {x: 3, y: 0, z: 4},
    ],
  },
];

export const ARGalleryScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<ARGalleryScreenRouteProp>();
  const {initialAssetId, projectId} = route.params;

  const assets = useSelector((state: AppState) => state.assets.assets);
  const projects = useSelector((state: AppState) => state.projects.projects);

  const [selectedAssets, setSelectedAssets] = useState<GalleryAsset[]>([]);
  const [selectedLayout, setSelectedLayout] = useState(GALLERY_LAYOUTS[0]);
  const [showAssetPicker, setShowAssetPicker] = useState(false);
  const [showLayoutPicker, setShowLayoutPicker] = useState(false);
  const [isPlacing, setIsPlacing] = useState(true);
  const [currentAssetIndex, setCurrentAssetIndex] = useState(0);
  const [galleryScale, setGalleryScale] = useState(1.0);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Add initial asset if provided
    if (initialAssetId) {
      const asset = assets.find(a => a.id === initialAssetId);
      if (asset) {
        addAssetToGallery(asset);
      }
    }

    // Fade in animation
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, [initialAssetId]);

  const addAssetToGallery = (asset: Asset) => {
    const positionIndex = selectedAssets.length % selectedLayout.positions.length;
    const position = selectedLayout.positions[positionIndex];

    const galleryAsset: GalleryAsset = {
      asset,
      position,
      rotation: {x: 0, y: 0, z: 0},
      scale: 1.0,
    };

    setSelectedAssets([...selectedAssets, galleryAsset]);
  };

  const removeAssetFromGallery = (index: number) => {
    setSelectedAssets(selectedAssets.filter((_, i) => i !== index));
  };

  const updateAssetPosition = (index: number, position: {x: number; y: number; z: number}) => {
    const updated = [...selectedAssets];
    updated[index].position = position;
    setSelectedAssets(updated);
  };

  const updateAssetScale = (index: number, scale: number) => {
    const updated = [...selectedAssets];
    updated[index].scale = scale;
    setSelectedAssets(updated);
  };

  const applyLayout = (layout: GalleryLayout) => {
    const updated = selectedAssets.map((item, index) => {
      const positionIndex = index % layout.positions.length;
      return {
        ...item,
        position: layout.positions[positionIndex],
      };
    });
    setSelectedAssets(updated);
    setSelectedLayout(layout);
  };

  const handleSaveGallery = async () => {
    // Save gallery configuration
    const galleryData = {
      layout: selectedLayout.name,
      scale: galleryScale,
      assets: selectedAssets.map(item => ({
        assetId: item.asset.id,
        position: item.position,
        rotation: item.rotation,
        scale: item.scale,
      })),
    };

    console.log('Saving gallery:', galleryData);
    // Would save to backend or local storage
  };

  const renderAssetPicker = () => (
    <Portal>
      <Dialog
        visible={showAssetPicker}
        onDismiss={() => setShowAssetPicker(false)}
        style={styles.dialog}>
        <Dialog.Title>Select Assets</Dialog.Title>
        <Dialog.ScrollArea>
          <ScrollView>
            {assets.map(asset => (
              <List.Item
                key={asset.id}
                title={asset.name}
                description={asset.metadata?.mime_type}
                left={(props) => (
                  <Icon
                    {...props}
                    name={
                      asset.metadata?.mime_type?.startsWith('image/') ? 'image' :
                      asset.metadata?.mime_type?.startsWith('video/') ? 'videocam' :
                      'insert-drive-file'
                    }
                    size={24}
                    color={colors.primary}
                  />
                )}
                right={(props) => (
                  selectedAssets.find(g => g.asset.id === asset.id) ? (
                    <Icon {...props} name="check" size={24} color={colors.success} />
                  ) : null
                )}
                onPress={() => {
                  if (!selectedAssets.find(g => g.asset.id === asset.id)) {
                    addAssetToGallery(asset);
                  }
                }}
              />
            ))}
          </ScrollView>
        </Dialog.ScrollArea>
        <Dialog.Actions>
          <Button onPress={() => setShowAssetPicker(false)}>Done</Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );

  const renderLayoutPicker = () => (
    <Portal>
      <Dialog
        visible={showLayoutPicker}
        onDismiss={() => setShowLayoutPicker(false)}>
        <Dialog.Title>Choose Layout</Dialog.Title>
        <Dialog.Content>
          <View style={styles.layoutGrid}>
            {GALLERY_LAYOUTS.map(layout => (
              <TouchableOpacity
                key={layout.name}
                style={[
                  styles.layoutOption,
                  selectedLayout.name === layout.name && styles.layoutOptionSelected,
                ]}
                onPress={() => {
                  applyLayout(layout);
                  setShowLayoutPicker(false);
                }}>
                <Icon 
                  name={layout.icon} 
                  size={48} 
                  color={
                    selectedLayout.name === layout.name 
                      ? colors.primary 
                      : colors.gray600
                  } 
                />
                <Text style={styles.layoutName}>{layout.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Dialog.Content>
      </Dialog>
    </Portal>
  );

  const renderGalleryControls = () => (
    <Card style={styles.controlsCard}>
      <Card.Content>
        <View style={styles.controlsHeader}>
          <Text style={styles.controlsTitle}>Gallery Controls</Text>
          <Chip mode="flat" compact>
            {selectedAssets.length} assets
          </Chip>
        </View>

        <View style={styles.controlsRow}>
          <Text style={styles.controlLabel}>Layout</Text>
          <Button
            mode="outlined"
            icon={selectedLayout.icon}
            onPress={() => setShowLayoutPicker(true)}>
            {selectedLayout.name}
          </Button>
        </View>

        <View style={styles.controlsRow}>
          <Text style={styles.controlLabel}>Gallery Scale</Text>
          <View style={styles.scaleControls}>
            <IconButton
              icon="minus"
              size={20}
              onPress={() => setGalleryScale(Math.max(0.5, galleryScale - 0.1))}
            />
            <Text style={styles.scaleValue}>{(galleryScale * 100).toFixed(0)}%</Text>
            <IconButton
              icon="plus"
              size={20}
              onPress={() => setGalleryScale(Math.min(2.0, galleryScale + 0.1))}
            />
          </View>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.assetsList}>
          {selectedAssets.map((item, index) => (
            <TouchableOpacity
              key={`${item.asset.id}_${index}`}
              style={[
                styles.assetThumb,
                currentAssetIndex === index && styles.assetThumbActive,
              ]}
              onPress={() => setCurrentAssetIndex(index)}>
              <View style={styles.assetThumbImage}>
                <Icon
                  name={
                    item.asset.metadata?.mime_type?.startsWith('image/') ? 'image' :
                    item.asset.metadata?.mime_type?.startsWith('video/') ? 'videocam' :
                    'insert-drive-file'
                  }
                  size={32}
                  color={currentAssetIndex === index ? colors.primary : colors.gray600}
                />
              </View>
              <IconButton
                icon="close"
                size={16}
                style={styles.removeButton}
                onPress={() => removeAssetFromGallery(index)}
              />
            </TouchableOpacity>
          ))}
          
          <TouchableOpacity
            style={styles.addAssetButton}
            onPress={() => setShowAssetPicker(true)}>
            <Icon name="add" size={32} color={colors.primary} />
          </TouchableOpacity>
        </ScrollView>
      </Card.Content>
    </Card>
  );

  return (
    <Animated.View style={[styles.container, {opacity: fadeAnim}]}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="AR Gallery" subtitle={`${selectedAssets.length} assets`} />
        <Appbar.Action icon="save" onPress={handleSaveGallery} />
        <Appbar.Action icon="share" onPress={() => {}} />
      </Appbar.Header>

      <View style={styles.arView}>
        <Canvas
          camera={{position: [0, 0, 5], fov: 75}}
          style={styles.canvas}>
          
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          
          <Environment preset="apartment" />
          
          {/* Gallery floor */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.5, 0]}>
            <planeGeometry args={[20, 20]} />
            <meshStandardMaterial color={colors.gray200} />
          </mesh>

          {/* Render gallery assets */}
          {selectedAssets.map((item, index) => (
            <group
              key={`${item.asset.id}_${index}`}
              position={[
                item.position.x * galleryScale,
                item.position.y * galleryScale,
                item.position.z * galleryScale,
              ]}>
              <mesh>
                <boxGeometry args={[1, 1, 0.1]} />
                <meshStandardMaterial color={colors.surface} />
              </mesh>
            </group>
          ))}
          
          <PerspectiveCamera makeDefault position={[0, 0, 5]} />
        </Canvas>
      </View>

      {renderGalleryControls()}

      <FAB
        icon={isPlacing ? 'check' : 'edit'}
        label={isPlacing ? 'Confirm Placement' : 'Edit Gallery'}
        onPress={() => setIsPlacing(!isPlacing)}
        style={styles.fab}
      />

      {renderAssetPicker()}
      {renderLayoutPicker()}
    </Animated.View>
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
  arView: {
    flex: 1,
  },
  canvas: {
    flex: 1,
  },
  controlsCard: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    elevation: 8,
  },
  controlsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  controlsTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  controlsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  controlLabel: {
    ...typography.bodyLarge,
    color: colors.onSurface,
  },
  scaleControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scaleValue: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginHorizontal: spacing.sm,
    minWidth: 40,
    textAlign: 'center',
  },
  assetsList: {
    marginTop: spacing.md,
    marginHorizontal: -spacing.md,
    paddingHorizontal: spacing.md,
  },
  assetThumb: {
    width: 80,
    height: 80,
    marginRight: spacing.sm,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.gray300,
    overflow: 'hidden',
    position: 'relative',
  },
  assetThumbActive: {
    borderColor: colors.primary,
  },
  assetThumbImage: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.gray100,
  },
  removeButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: colors.error,
    margin: 0,
  },
  addAssetButton: {
    width: 80,
    height: 80,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.primary,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 240,
  },
  dialog: {
    maxHeight: '80%',
  },
  layoutGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
  },
  layoutOption: {
    width: (screenWidth - spacing.lg * 4) / 2,
    padding: spacing.md,
    margin: spacing.sm,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.gray300,
    alignItems: 'center',
  },
  layoutOptionSelected: {
    borderColor: colors.primary,
    backgroundColor: `${colors.primary}10`,
  },
  layoutName: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginTop: spacing.sm,
  },
});