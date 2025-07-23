/**
 * Location Service
 * 
 * Handles GPS location tracking, geocoding,
 * and location tagging for media assets.
 */

import Geolocation from 'react-native-geolocation-service';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import {Platform, Alert} from 'react-native';
import Geocoding from 'react-native-geocoding';

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy: number;
  altitude?: number;
  heading?: number;
  speed?: number;
  timestamp: number;
}

export interface LocationAddress {
  address: string;
  city?: string;
  state?: string;
  country?: string;
  postalCode?: string;
  formattedAddress: string;
}

export interface LocationTag {
  id: string;
  coordinates: LocationData;
  address: LocationAddress;
  name?: string;
  category?: 'home' | 'work' | 'event' | 'travel' | 'custom';
  created_at: string;
  used_count: number;
}

class LocationService {
  private watchId: number | null = null;
  private isTracking = false;
  private geocodingApiKey = 'YOUR_GOOGLE_MAPS_API_KEY'; // Replace with actual API key

  constructor() {
    // Initialize geocoding with API key
    Geocoding.init(this.geocodingApiKey);
  }

  /**
   * Check location permissions
   */
  async checkLocationPermissions(): Promise<boolean> {
    try {
      const permission = Platform.OS === 'ios' 
        ? PERMISSIONS.IOS.LOCATION_WHEN_IN_USE
        : PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION;
      
      const result = await check(permission);
      return result === RESULTS.GRANTED;
    } catch (error) {
      console.error('Error checking location permissions:', error);
      return false;
    }
  }

  /**
   * Request location permissions
   */
  async requestLocationPermissions(): Promise<boolean> {
    try {
      const permission = Platform.OS === 'ios'
        ? PERMISSIONS.IOS.LOCATION_WHEN_IN_USE
        : PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION;
      
      const result = await request(permission);
      return result === RESULTS.GRANTED;
    } catch (error) {
      console.error('Error requesting location permissions:', error);
      return false;
    }
  }

  /**
   * Get current location
   */
  async getCurrentLocation(options: {
    timeout?: number;
    maximumAge?: number;
    enableHighAccuracy?: boolean;
  } = {}): Promise<LocationData | null> {
    try {
      // Check permissions first
      const hasPermission = await this.checkLocationPermissions();
      if (!hasPermission) {
        const granted = await this.requestLocationPermissions();
        if (!granted) {
          Alert.alert(
            'Location Permission Required',
            'Please grant location permissions to tag media with location.',
            [
              {text: 'Cancel'},
              {text: 'Settings', onPress: () => this.openSettings()},
            ]
          );
          return null;
        }
      }

      return new Promise((resolve, reject) => {
        Geolocation.getCurrentPosition(
          (position) => {
            const location: LocationData = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy,
              altitude: position.coords.altitude || undefined,
              heading: position.coords.heading || undefined,
              speed: position.coords.speed || undefined,
              timestamp: position.timestamp,
            };
            resolve(location);
          },
          (error) => {
            console.error('Error getting current location:', error);
            reject(error);
          },
          {
            enableHighAccuracy: options.enableHighAccuracy ?? true,
            timeout: options.timeout ?? 15000,
            maximumAge: options.maximumAge ?? 10000,
          }
        );
      });
    } catch (error) {
      console.error('Error in getCurrentLocation:', error);
      return null;
    }
  }

  /**
   * Start location tracking
   */
  startLocationTracking(
    onLocationUpdate: (location: LocationData) => void,
    options: {
      distanceFilter?: number;
      interval?: number;
      enableHighAccuracy?: boolean;
    } = {}
  ): boolean {
    try {
      if (this.isTracking) {
        this.stopLocationTracking();
      }

      this.watchId = Geolocation.watchPosition(
        (position) => {
          const location: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude || undefined,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: position.timestamp,
          };
          onLocationUpdate(location);
        },
        (error) => {
          console.error('Location tracking error:', error);
        },
        {
          enableHighAccuracy: options.enableHighAccuracy ?? false,
          distanceFilter: options.distanceFilter ?? 10,
          interval: options.interval ?? 5000,
        }
      );

      this.isTracking = true;
      return true;
    } catch (error) {
      console.error('Error starting location tracking:', error);
      return false;
    }
  }

  /**
   * Stop location tracking
   */
  stopLocationTracking(): void {
    if (this.watchId !== null) {
      Geolocation.clearWatch(this.watchId);
      this.watchId = null;
      this.isTracking = false;
    }
  }

  /**
   * Get address from coordinates (reverse geocoding)
   */
  async getAddressFromCoordinates(latitude: number, longitude: number): Promise<LocationAddress | null> {
    try {
      const response = await Geocoding.from(latitude, longitude);
      
      if (response.results.length > 0) {
        const result = response.results[0];
        const components = result.address_components;
        
        const address: LocationAddress = {
          address: result.formatted_address,
          formattedAddress: result.formatted_address,
        };

        // Extract address components
        components.forEach((component: any) => {
          const types = component.types;
          
          if (types.includes('locality')) {
            address.city = component.long_name;
          } else if (types.includes('administrative_area_level_1')) {
            address.state = component.long_name;
          } else if (types.includes('country')) {
            address.country = component.long_name;
          } else if (types.includes('postal_code')) {
            address.postalCode = component.long_name;
          }
        });

        return address;
      }
      
      return null;
    } catch (error) {
      console.error('Error getting address from coordinates:', error);
      return null;
    }
  }

  /**
   * Get coordinates from address (forward geocoding)
   */
  async getCoordinatesFromAddress(address: string): Promise<LocationData | null> {
    try {
      const response = await Geocoding.from(address);
      
      if (response.results.length > 0) {
        const location = response.results[0].geometry.location;
        
        return {
          latitude: location.lat,
          longitude: location.lng,
          accuracy: 100, // Estimated accuracy for geocoded results
          timestamp: Date.now(),
        };
      }
      
      return null;
    } catch (error) {
      console.error('Error getting coordinates from address:', error);
      return null;
    }
  }

  /**
   * Calculate distance between two points (in meters)
   */
  calculateDistance(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δφ = ((lat2 - lat1) * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;

    const a =
      Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
      Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
  }

  /**
   * Format location for display
   */
  formatLocationForDisplay(location: LocationData, address?: LocationAddress): string {
    if (address) {
      return address.city && address.state
        ? `${address.city}, ${address.state}`
        : address.formattedAddress;
    }
    
    return `${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`;
  }

  /**
   * Create location tag from current location
   */
  async createLocationTag(
    name?: string,
    category: LocationTag['category'] = 'custom'
  ): Promise<LocationTag | null> {
    try {
      const location = await this.getCurrentLocation();
      if (!location) return null;

      const address = await this.getAddressFromCoordinates(
        location.latitude,
        location.longitude
      );

      const locationTag: LocationTag = {
        id: `location_${Date.now()}`,
        coordinates: location,
        address: address || {
          address: 'Unknown location',
          formattedAddress: `${location.latitude}, ${location.longitude}`,
        },
        name: name || address?.city || 'New Location',
        category,
        created_at: new Date().toISOString(),
        used_count: 0,
      };

      return locationTag;
    } catch (error) {
      console.error('Error creating location tag:', error);
      return null;
    }
  }

  /**
   * Get nearby saved locations
   */
  async getNearbyLocations(
    currentLocation: LocationData,
    savedLocations: LocationTag[],
    radiusMeters = 1000
  ): Promise<LocationTag[]> {
    try {
      return savedLocations.filter(location => {
        const distance = this.calculateDistance(
          currentLocation.latitude,
          currentLocation.longitude,
          location.coordinates.latitude,
          location.coordinates.longitude
        );
        return distance <= radiusMeters;
      });
    } catch (error) {
      console.error('Error getting nearby locations:', error);
      return [];
    }
  }

  /**
   * Check if location services are enabled
   */
  async isLocationServicesEnabled(): Promise<boolean> {
    try {
      // This would check if location services are enabled on the device
      // Implementation depends on platform and available libraries
      return true;
    } catch (error) {
      console.error('Error checking location services:', error);
      return false;
    }
  }

  /**
   * Get location accuracy description
   */
  getAccuracyDescription(accuracy: number): string {
    if (accuracy <= 5) return 'Excellent';
    if (accuracy <= 10) return 'Good';
    if (accuracy <= 50) return 'Fair';
    if (accuracy <= 100) return 'Poor';
    return 'Very Poor';
  }

  /**
   * Open device settings
   */
  private openSettings(): void {
    // This would open device location settings
    // Implementation depends on platform and available libraries
    console.log('Opening location settings...');
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    this.stopLocationTracking();
  }
}

export const locationService = new LocationService();