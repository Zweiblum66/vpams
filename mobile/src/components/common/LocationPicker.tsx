/**
 * Location Picker Component
 * 
 * Reusable component for selecting location tags
 * in upload and asset editing flows.
 */

import React, {useState, useEffect} from 'react';
import {
  View,
  StyleSheet,
  Alert,
} from 'react-native';
import {
  Card,
  Text,
  Button,
  Chip,
  List,
  Portal,
  Modal,
  ActivityIndicator,
  Divider,
} from 'react-native-paper';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState} from '@/types';
import {
  getCurrentLocation,
  createLocationTag,
  findNearbyLocations,
  incrementLocationUsage,
} from '@/store/slices/locationSlice';
import {LocationTag, locationService} from '@/services/locationService';
import {colors, spacing, typography} from '@/constants/theme';

interface LocationPickerProps {
  selectedLocation?: LocationTag | null;
  onLocationChange: (location: LocationTag | null) => void;
  showNearby?: boolean;
  allowCreate?: boolean;
  style?: any;
}

export const LocationPicker: React.FC<LocationPickerProps> = ({
  selectedLocation,
  onLocationChange,
  showNearby = true,
  allowCreate = true,
  style,
}) => {
  const dispatch = useDispatch();
  
  const {
    currentLocation,
    savedLocations,
    recentLocations,
    isLoading,
    permissionsGranted,
  } = useSelector((state: AppState) => state.location);

  const [modalVisible, setModalVisible] = useState(false);
  const [nearbyLocations, setNearbyLocations] = useState<LocationTag[]>([]);
  const [isGettingLocation, setIsGettingLocation] = useState(false);

  useEffect(() => {
    if (showNearby && currentLocation) {
      findNearby();
    }
  }, [currentLocation, showNearby]);

  const findNearby = async () => {
    if (!currentLocation) return;
    
    try {
      const nearby = await locationService.getNearbyLocations(
        currentLocation,
        savedLocations,
        1000 // 1km radius
      );
      setNearbyLocations(nearby);
    } catch (error) {
      console.error('Error finding nearby locations:', error);
    }
  };

  const handleSelectLocation = (location: LocationTag) => {
    onLocationChange(location);
    dispatch(incrementLocationUsage(location.id));
    setModalVisible(false);
  };

  const handleUseCurrentLocation = async () => {
    if (!permissionsGranted) {
      Alert.alert(
        'Location Permission Required',
        'Please grant location permissions to use current location.',
        [
          {text: 'Cancel'},
          {text: 'Grant', onPress: () => {/* Open settings */}},
        ]
      );
      return;
    }

    setIsGettingLocation(true);
    
    try {
      const location = await dispatch(getCurrentLocation()).unwrap();
      
      // Create a temporary location tag
      const address = await locationService.getAddressFromCoordinates(
        location.latitude,
        location.longitude
      );
      
      const locationTag: LocationTag = {
        id: `current_${Date.now()}`,
        coordinates: location,
        address: address || {
          address: 'Current location',
          formattedAddress: `${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`,
        },
        name: address?.city || 'Current Location',
        category: 'custom',
        created_at: new Date().toISOString(),
        used_count: 0,
      };
      
      onLocationChange(locationTag);
      setModalVisible(false);
    } catch (error) {
      Alert.alert('Error', 'Failed to get current location');
    } finally {
      setIsGettingLocation(false);
    }
  };

  const handleCreateFromCurrent = async () => {
    try {
      const locationTag = await dispatch(createLocationTag({
        name: 'New Location',
        category: 'custom',
      })).unwrap();
      
      onLocationChange(locationTag);
      setModalVisible(false);
    } catch (error) {
      Alert.alert('Error', 'Failed to create location tag');
    }
  };

  const renderLocationModal = () => (
    <Portal>
      <Modal
        visible={modalVisible}
        onDismiss={() => setModalVisible(false)}
        contentContainerStyle={styles.modal}>
        
        <Text style={styles.modalTitle}>Select Location</Text>
        
        {/* Current location option */}
        <List.Item
          title="Use Current Location"
          description={
            currentLocation
              ? `${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}`
              : 'Getting location...'
          }
          left={(props) => (
            <Icon {...props} name="my-location" size={24} color={colors.primary} />
          )}
          right={() => (
            isGettingLocation ? (
              <ActivityIndicator size="small" />
            ) : (
              <Icon name="chevron-right" size={24} color={colors.gray400} />
            )
          )}
          onPress={handleUseCurrentLocation}
          disabled={isGettingLocation || !permissionsGranted}
          style={styles.locationOption}
        />
        
        <Divider />
        
        {/* Nearby locations */}
        {showNearby && nearbyLocations.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Nearby Locations</Text>
            {nearbyLocations.slice(0, 3).map(location => (
              <List.Item
                key={location.id}
                title={location.name}
                description={location.address.formattedAddress}
                left={(props) => (
                  <Icon {...props} name="place" size={24} color={colors.secondary} />
                )}
                right={() => (
                  <Chip mode="flat" compact>
                    {location.category}
                  </Chip>
                )}
                onPress={() => handleSelectLocation(location)}
                style={styles.locationOption}
              />
            ))}
            <Divider />
          </>
        )}
        
        {/* Recent locations */}
        {recentLocations.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Recent Locations</Text>
            {recentLocations.slice(0, 3).map(location => (
              <List.Item
                key={location.id}
                title={location.name}
                description={location.address.formattedAddress}
                left={(props) => (
                  <Icon {...props} name="history" size={24} color={colors.gray600} />
                )}
                onPress={() => handleSelectLocation(location)}
                style={styles.locationOption}
              />
            ))}
            <Divider />
          </>
        )}
        
        {/* Saved locations */}
        {savedLocations.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Saved Locations</Text>
            {savedLocations.slice(0, 5).map(location => (
              <List.Item
                key={location.id}
                title={location.name}
                description={location.address.formattedAddress}
                left={(props) => (
                  <Icon {...props} name="bookmark" size={24} color={colors.primary} />
                )}
                right={() => (
                  <Chip mode="flat" compact>
                    {location.category}
                  </Chip>
                )}
                onPress={() => handleSelectLocation(location)}
                style={styles.locationOption}
              />
            ))}
          </>
        )}
        
        {/* Action buttons */}
        <View style={styles.modalActions}>
          {allowCreate && (
            <Button
              mode="outlined"
              icon="plus"
              onPress={handleCreateFromCurrent}
              style={styles.actionButton}>
              Save Current Location
            </Button>
          )}
          
          <Button
            mode="outlined"
            icon="map"
            onPress={() => {
              setModalVisible(false);
              // Navigate to full location picker
            }}
            style={styles.actionButton}>
            Browse All Locations
          </Button>
          
          <Button
            mode="contained"
            onPress={() => setModalVisible(false)}
            style={styles.actionButton}>
            Cancel
          </Button>
        </View>
      </Modal>
    </Portal>
  );

  return (
    <>
      <Card style={[styles.container, style]}>
        <Card.Content>
          <View style={styles.header}>
            <Text style={styles.label}>Location</Text>
            {selectedLocation && (
              <Chip
                mode="flat"
                onClose={() => onLocationChange(null)}
                style={styles.categoryChip}>
                {selectedLocation.category}
              </Chip>
            )}
          </View>
          
          {selectedLocation ? (
            <View style={styles.selectedLocation}>
              <Icon name="place" size={20} color={colors.primary} />
              <View style={styles.locationInfo}>
                <Text style={styles.locationName}>{selectedLocation.name}</Text>
                <Text style={styles.locationAddress}>
                  {selectedLocation.address.formattedAddress}
                </Text>
              </View>
            </View>
          ) : (
            <Text style={styles.noLocationText}>No location selected</Text>
          )}
          
          <Button
            mode="outlined"
            icon={selectedLocation ? "edit-location" : "add-location"}
            onPress={() => setModalVisible(true)}
            style={styles.selectButton}>
            {selectedLocation ? 'Change Location' : 'Add Location'}
          </Button>
        </Card.Content>
      </Card>
      
      {renderLocationModal()}
    </>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '500',
  },
  categoryChip: {
    height: 24,
  },
  selectedLocation: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
    padding: spacing.sm,
    backgroundColor: colors.primaryContainer,
    borderRadius: 8,
  },
  locationInfo: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  locationName: {
    ...typography.bodyLarge,
    color: colors.onPrimaryContainer,
    fontWeight: '500',
  },
  locationAddress: {
    ...typography.bodySmall,
    color: colors.onPrimaryContainer,
    opacity: 0.8,
    marginTop: 2,
  },
  noLocationText: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginBottom: spacing.md,
    textAlign: 'center',
    padding: spacing.md,
  },
  selectButton: {
    marginTop: spacing.xs,
  },
  modal: {
    backgroundColor: colors.surface,
    margin: spacing.lg,
    borderRadius: 12,
    maxHeight: '80%',
  },
  modalTitle: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    textAlign: 'center',
    padding: spacing.lg,
    paddingBottom: spacing.md,
  },
  sectionTitle: {
    ...typography.titleSmall,
    color: colors.onSurface,
    fontWeight: '600',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceVariant,
  },
  locationOption: {
    paddingHorizontal: spacing.lg,
  },
  modalActions: {
    padding: spacing.lg,
    paddingTop: spacing.md,
  },
  actionButton: {
    marginBottom: spacing.sm,
  },
});