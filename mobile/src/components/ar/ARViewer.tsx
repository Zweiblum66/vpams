/**
 * AR Viewer Component
 * 
 * Reusable AR viewer component that can be embedded
 * in various screens for quick AR preview.
 */

import React, {useState, useEffect} from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
} from 'react-native';
import {
  Card,
  Text,
  IconButton,
  ProgressBar,
  Chip,
  Portal,
  Dialog,
  List,
  Button,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useNavigation} from '@react-navigation/native';

import {Asset} from '@/types';
import {arService, ARCapabilities, ARPreviewType} from '@/services/arService';
import {colors, spacing, typography} from '@/constants/theme';

interface ARViewerProps {
  asset: Asset;
  compact?: boolean;
  showPreviewButton?: boolean;
  onARStart?: () => void;
  onAREnd?: () => void;
}

export const ARViewer: React.FC<ARViewerProps> = ({
  asset,
  compact = false,
  showPreviewButton = true,
  onARStart,
  onAREnd,
}) => {
  const navigation = useNavigation();
  const [arCapabilities, setARCapabilities] = useState<ARCapabilities | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [previewType, setPreviewType] = useState<ARPreviewType | null>(null);
  const [showARDialog, setShowARDialog] = useState(false);

  useEffect(() => {
    checkARCapabilities();
  }, [asset]);

  const checkARCapabilities = async () => {
    setIsChecking(true);
    try {
      const capabilities = await arService.checkARSupport();
      setARCapabilities(capabilities);
      
      if (capabilities.isSupported) {
        const type = arService.getPreviewTypeForAsset(asset);
        setPreviewType(type);
      }
    } catch (error) {
      console.error('Failed to check AR capabilities:', error);
    } finally {
      setIsChecking(false);
    }
  };

  const handleStartAR = () => {
    if (!arCapabilities?.isSupported) {
      Alert.alert(
        'AR Not Supported',
        'Your device does not support AR features.',
        [{text: 'OK'}]
      );
      return;
    }

    if (!previewType) {
      Alert.alert(
        'Preview Not Available',
        'AR preview is not available for this type of asset.',
        [{text: 'OK'}]
      );
      return;
    }

    onARStart?.();
    navigation.navigate('ARPreview' as never, {
      assetId: asset.id,
      previewType,
    } as never);
  };

  const getPreviewIcon = () => {
    switch (previewType) {
      case 'image_on_wall':
        return 'picture-in-picture';
      case 'video_screen':
        return 'tv';
      case '3d_model':
        return 'view-in-ar';
      case 'document_viewer':
        return 'article';
      case 'virtual_gallery':
        return 'museum';
      default:
        return 'view-in-ar';
    }
  };

  const getPreviewDescription = () => {
    switch (previewType) {
      case 'image_on_wall':
        return 'View image on your wall';
      case 'video_screen':
        return 'Watch on virtual screen';
      case '3d_model':
        return 'Place 3D model in space';
      case 'document_viewer':
        return 'Read in AR space';
      case 'virtual_gallery':
        return 'Create virtual gallery';
      default:
        return 'View in AR';
    }
  };

  const renderCompactView = () => {
    if (!arCapabilities?.isSupported || !previewType) {
      return null;
    }

    return (
      <TouchableOpacity
        style={styles.compactContainer}
        onPress={handleStartAR}
        disabled={isChecking}>
        <Icon 
          name={getPreviewIcon()} 
          size={24} 
          color={colors.primary} 
        />
        <Text style={styles.compactText}>AR</Text>
      </TouchableOpacity>
    );
  };

  const renderFullView = () => {
    if (isChecking) {
      return (
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.loadingContainer}>
              <ProgressBar indeterminate />
              <Text style={styles.loadingText}>
                Checking AR capabilities...
              </Text>
            </View>
          </Card.Content>
        </Card>
      );
    }

    if (!arCapabilities?.isSupported) {
      return (
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.notSupportedContainer}>
              <Icon 
                name="warning" 
                size={48} 
                color={colors.warning} 
              />
              <Text style={styles.notSupportedText}>
                AR Preview Not Available
              </Text>
              <Text style={styles.notSupportedDescription}>
                Your device doesn't support AR features
              </Text>
            </View>
          </Card.Content>
        </Card>
      );
    }

    if (!previewType) {
      return null;
    }

    return (
      <Card style={styles.card}>
        <TouchableOpacity onPress={() => setShowARDialog(true)}>
          <Card.Cover 
            source={{uri: asset.thumbnail_url || asset.proxy_url}} 
            style={styles.preview}
          />
          <View style={styles.arOverlay}>
            <Icon 
              name={getPreviewIcon()} 
              size={64} 
              color={colors.white} 
            />
            <Text style={styles.arOverlayText}>
              Tap to view in AR
            </Text>
          </View>
        </TouchableOpacity>
        
        <Card.Content style={styles.cardContent}>
          <View style={styles.infoContainer}>
            <Icon 
              name={getPreviewIcon()} 
              size={24} 
              color={colors.primary} 
            />
            <View style={styles.textContainer}>
              <Text style={styles.previewTitle}>
                AR Preview Available
              </Text>
              <Text style={styles.previewDescription}>
                {getPreviewDescription()}
              </Text>
            </View>
          </View>
          
          <View style={styles.featuresContainer}>
            {arCapabilities.supportedFeatures.map((feature) => (
              <Chip
                key={feature}
                mode="outlined"
                compact
                style={styles.featureChip}>
                {feature.replace(/_/g, ' ')}
              </Chip>
            ))}
          </View>
        </Card.Content>
        
        {showPreviewButton && (
          <Card.Actions>
            <Button
              mode="contained"
              icon="view-in-ar"
              onPress={handleStartAR}>
              Start AR Preview
            </Button>
          </Card.Actions>
        )}
      </Card>
    );
  };

  const renderARDialog = () => (
    <Portal>
      <Dialog
        visible={showARDialog}
        onDismiss={() => setShowARDialog(false)}>
        <Dialog.Title>AR Preview Options</Dialog.Title>
        <Dialog.Content>
          <List.Section>
            <List.Item
              title="Quick Preview"
              description="View asset in AR space"
              left={(props) => <List.Icon {...props} icon="view-in-ar" />}
              onPress={() => {
                setShowARDialog(false);
                handleStartAR();
              }}
            />
            <List.Item
              title="Virtual Gallery"
              description="Create a gallery with multiple assets"
              left={(props) => <List.Icon {...props} icon="museum" />}
              onPress={() => {
                setShowARDialog(false);
                navigation.navigate('ARGallery' as never, {
                  initialAssetId: asset.id,
                } as never);
              }}
            />
            <List.Item
              title="AR Measure"
              description="Measure real-world dimensions"
              left={(props) => <List.Icon {...props} icon="straighten" />}
              onPress={() => {
                setShowARDialog(false);
                Alert.alert('Coming Soon', 'AR measurement feature coming soon!');
              }}
            />
          </List.Section>
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={() => setShowARDialog(false)}>Cancel</Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );

  return (
    <>
      {compact ? renderCompactView() : renderFullView()}
      {renderARDialog()}
    </>
  );
};

const styles = StyleSheet.create({
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.sm,
    borderRadius: 4,
    backgroundColor: `${colors.primary}10`,
  },
  compactText: {
    ...typography.bodySmall,
    color: colors.primary,
    marginLeft: spacing.xs,
    fontWeight: '600',
  },
  card: {
    marginVertical: spacing.sm,
    overflow: 'hidden',
  },
  preview: {
    height: 200,
    backgroundColor: colors.gray200,
  },
  arOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: `${colors.black}80`,
    justifyContent: 'center',
    alignItems: 'center',
  },
  arOverlayText: {
    ...typography.titleMedium,
    color: colors.white,
    marginTop: spacing.sm,
  },
  cardContent: {
    paddingTop: spacing.md,
  },
  infoContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  textContainer: {
    flex: 1,
    marginLeft: spacing.md,
  },
  previewTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  previewDescription: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  featuresContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.md,
  },
  featureChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
  loadingContainer: {
    alignItems: 'center',
    padding: spacing.lg,
  },
  loadingText: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.md,
  },
  notSupportedContainer: {
    alignItems: 'center',
    padding: spacing.xl,
  },
  notSupportedText: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginTop: spacing.md,
    fontWeight: '600',
  },
  notSupportedDescription: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
});