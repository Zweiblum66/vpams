/**
 * Location Tagging Screen
 * 
 * Interface for viewing, managing, and creating location tags
 * with map integration and location search.
 */

import React, {useState, useEffect, useCallback} from 'react';
import {
  View,
  StyleSheet,
  Alert,
  Dimensions,
  FlatList,
  ScrollView,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  TextInput,
  Button,
  Chip,
  List,
  FAB,
  SearchBar,
  Divider,
  Switch,
  SegmentedButtons,
  ActivityIndicator,
} from 'react-native-paper';
import {useNavigation, useRoute} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import MapView, {Marker, Region} from 'react-native-maps';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState} from '@/types';
import {
  initializeLocation,
  getCurrentLocation,
  createLocationTag,
  findNearbyLocations,
  addSavedLocation,
  removeSavedLocation,
  incrementLocationUsage,
  updateLocationSettings,
} from '@/store/slices/locationSlice';
import {LocationTag, LocationData} from '@/services/locationService';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth, height: screenHeight} = Dimensions.get('window');

interface LocationTaggingScreenProps {
  route?: {
    params?: {
      assetId?: string;
      onLocationSelected?: (location: LocationTag) => void;
      mode?: 'select' | 'manage';
    };
  };
}

export const LocationTaggingScreen: React.FC<LocationTaggingScreenProps> = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const dispatch = useDispatch();
  
  const {
    currentLocation,
    savedLocations,
    recentLocations,
    isLoading,
    error,
    settings,
    permissionsGranted,
  } = useSelector((state: AppState) => state.location);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<LocationTag | null>(null);
  const [mapRegion, setMapRegion] = useState<Region | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newLocationName, setNewLocationName] = useState('');
  const [newLocationCategory, setNewLocationCategory] = useState<LocationTag['category']>('custom');

  const params = route.params as LocationTaggingScreenProps['route']['params'];
  const mode = params?.mode || 'manage';
  const onLocationSelected = params?.onLocationSelected;

  useEffect(() => {
    initializeLocationServices();
  }, []);

  useEffect(() => {
    if (currentLocation && !mapRegion) {
      setMapRegion({
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      });
    }
  }, [currentLocation, mapRegion]);

  const initializeLocationServices = async () => {
    try {
      await dispatch(initializeLocation()).unwrap();
      if (permissionsGranted) {
        await dispatch(getCurrentLocation()).unwrap();
        await dispatch(findNearbyLocations()).unwrap();
      }
    } catch (error) {
      console.error('Failed to initialize location services:', error);
    }
  };

  const handleLocationSelect = useCallback((location: LocationTag) => {
    setSelectedLocation(location);
    
    if (mode === 'select' && onLocationSelected) {
      dispatch(incrementLocationUsage(location.id));
      onLocationSelected(location);
      navigation.goBack();
    } else {
      // Pan map to selected location
      setMapRegion({
        latitude: location.coordinates.latitude,
        longitude: location.coordinates.longitude,
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      });
    }
  }, [mode, onLocationSelected, dispatch, navigation]);

  const handleCreateLocation = async () => {
    try {
      if (!newLocationName.trim()) {
        Alert.alert('Error', 'Please enter a location name');
        return;
      }

      const locationTag = await dispatch(createLocationTag({
        name: newLocationName.trim(),
        category: newLocationCategory,
      })).unwrap();

      setShowCreateModal(false);
      setNewLocationName('');
      setNewLocationCategory('custom');
      
      Alert.alert('Success', 'Location saved successfully');
      
      if (mode === 'select' && onLocationSelected) {
        onLocationSelected(locationTag);
        navigation.goBack();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to create location tag');
    }
  };

  const handleDeleteLocation = (locationId: string) => {
    Alert.alert(
      'Delete Location',
      'Are you sure you want to delete this location?',
      [
        {text: 'Cancel'},
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => dispatch(removeSavedLocation(locationId)),
        },
      ]
    );
  };

  const handleGetCurrentLocation = async () => {
    try {
      const location = await dispatch(getCurrentLocation()).unwrap();
      setMapRegion({
        latitude: location.latitude,
        longitude: location.longitude,
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      });
    } catch (error) {
      Alert.alert('Error', 'Failed to get current location');
    }
  };

  const filteredLocations = savedLocations.filter(location => {
    const matchesSearch = location.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         location.address.formattedAddress.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || location.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const renderLocationItem = ({item}: {item: LocationTag}) => (
    <Card style={styles.locationCard} onPress={() => handleLocationSelect(item)}>
      <Card.Content>
        <View style={styles.locationHeader}>
          <Text style={styles.locationName}>{item.name}</Text>
          <Chip mode="flat" style={styles.categoryChip}>
            {item.category}
          </Chip>
        </View>
        
        <Text style={styles.locationAddress}>{item.address.formattedAddress}</Text>
        
        <View style={styles.locationMeta}>
          <Text style={styles.locationMetaText}>
            Used {item.used_count} times
          </Text>
          <Text style={styles.locationMetaText}>
            {new Date(item.created_at).toLocaleDateString()}
          </Text>
        </View>
        
        {mode === 'manage' && (
          <View style={styles.locationActions}>
            <Button
              mode="outlined"
              icon="edit"
              compact
              onPress={() => {
                // Navigate to edit screen
              }}>
              Edit
            </Button>
            <Button
              mode="outlined"
              icon="delete"
              compact
              textColor={colors.error}
              onPress={() => handleDeleteLocation(item.id)}>
              Delete
            </Button>
          </View>
        )}
      </Card.Content>
    </Card>
  );

  const renderMapView = () => (
    <View style={styles.mapContainer}>
      {mapRegion && (
        <MapView
          style={styles.map}
          region={mapRegion}
          onRegionChangeComplete={setMapRegion}
          showsUserLocation
          showsMyLocationButton={false}>
          
          {/* Current location marker */}
          {currentLocation && (
            <Marker
              coordinate={{
                latitude: currentLocation.latitude,
                longitude: currentLocation.longitude,
              }}
              title="Current Location"
              pinColor={colors.primary}
            />
          )}
          
          {/* Saved location markers */}
          {filteredLocations.map(location => (
            <Marker
              key={location.id}
              coordinate={{
                latitude: location.coordinates.latitude,
                longitude: location.coordinates.longitude,
              }}
              title={location.name}
              description={location.address.formattedAddress}
              pinColor={selectedLocation?.id === location.id ? colors.secondary : colors.gray400}
              onPress={() => handleLocationSelect(location)}
            />
          ))}
        </MapView>
      )}
      
      {/* Map controls */}
      <View style={styles.mapControls}>
        <Button
          mode="contained"
          icon="my-location"
          onPress={handleGetCurrentLocation}
          style={styles.locationButton}>
          My Location
        </Button>
      </View>
    </View>
  );

  const renderListView = () => (
    <FlatList
      data={filteredLocations}
      renderItem={renderLocationItem}
      keyExtractor={(item) => item.id}
      style={styles.locationsList}
      contentContainerStyle={styles.locationsListContent}
      showsVerticalScrollIndicator={false}
      ListEmptyComponent={
        <View style={styles.emptyState}>
          <Icon name="location-off" size={64} color={colors.gray400} />
          <Text style={styles.emptyStateText}>No saved locations</Text>
          <Text style={styles.emptyStateSubtext}>
            Create your first location tag to get started
          </Text>
        </View>
      }
    />
  );

  const renderCreateLocationModal = () => (
    // This would be implemented as a modal or bottom sheet
    // For now, it's a placeholder
    null
  );

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content 
          title={mode === 'select' ? 'Select Location' : 'Location Tags'} 
        />
        {mode === 'manage' && (
          <Appbar.Action
            icon="settings"
            onPress={() => navigation.navigate('LocationSettings' as never)}
          />
        )}
      </Appbar.Header>

      {/* Search and filters */}
      <View style={styles.searchContainer}>
        <TextInput
          label="Search locations"
          value={searchQuery}
          onChangeText={setSearchQuery}
          style={styles.searchInput}
          left={<TextInput.Icon icon="magnify" />}
          right={searchQuery ? <TextInput.Icon icon="close" onPress={() => setSearchQuery('')} /> : undefined}
        />
        
        <SegmentedButtons
          value={viewMode}
          onValueChange={setViewMode}
          buttons={[
            {value: 'map', label: 'Map', icon: 'map'},
            {value: 'list', label: 'List', icon: 'view-list'},
          ]}
          style={styles.viewModeSelector}
        />
        
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryFilters}>
          {['all', 'home', 'work', 'event', 'travel', 'custom'].map(category => (
            <Chip
              key={category}
              mode={categoryFilter === category ? 'flat' : 'outlined'}
              selected={categoryFilter === category}
              onPress={() => setCategoryFilter(category)}
              style={styles.categoryFilter}>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </Chip>
          ))}
        </ScrollView>
      </View>

      {/* Content */}
      <View style={styles.content}>
        {isLoading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>Loading locations...</Text>
          </View>
        )}
        
        {!isLoading && (
          <>
            {viewMode === 'map' ? renderMapView() : renderListView()}
          </>
        )}
      </View>

      {/* Add location FAB */}
      <FAB
        icon="plus"
        label="Add Location"
        onPress={() => setShowCreateModal(true)}
        style={styles.fab}
      />

      {renderCreateLocationModal()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  appBar: {
    backgroundColor: colors.primary,
  },
  searchContainer: {
    padding: spacing.md,
    backgroundColor: colors.surface,
  },
  searchInput: {
    marginBottom: spacing.sm,
    backgroundColor: colors.background,
  },
  viewModeSelector: {
    marginBottom: spacing.sm,
  },
  categoryFilters: {
    flexDirection: 'row',
  },
  categoryFilter: {
    marginRight: spacing.sm,
  },
  content: {
    flex: 1,
  },
  mapContainer: {
    flex: 1,
    position: 'relative',
  },
  map: {
    flex: 1,
  },
  mapControls: {
    position: 'absolute',
    top: spacing.md,
    right: spacing.md,
  },
  locationButton: {
    backgroundColor: colors.surface,
  },
  locationsList: {
    flex: 1,
  },
  locationsListContent: {
    padding: spacing.md,
  },
  locationCard: {
    marginBottom: spacing.md,
  },
  locationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  locationName: {
    ...typography.titleMedium,
    color: colors.onSurface,
    flex: 1,
  },
  categoryChip: {
    marginLeft: spacing.sm,
  },
  locationAddress: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginBottom: spacing.sm,
  },
  locationMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  locationMetaText: {
    ...typography.bodySmall,
    color: colors.gray500,
  },
  locationActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyStateText: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  emptyStateSubtext: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.md,
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
});