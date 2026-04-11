// Enhanced location tracking with improved accuracy for both desktop and mobile

class LocationTrackingService {
  constructor() {
    this.watchId = null;
    this.isTracking = false;
    this.lastUpdate = null;
    this.updateInterval = 30 * 1000; // 30 seconds default
    this.minDistance = 50; // Minimum distance in meters to trigger update
    this.lastPosition = null;
    this.token = null;
    this.onLocationUpdate = null;
    this.onError = null;
    this.onPermissionChange = null;
    this.isMobileDevice = this.detectMobileDevice();
    
    // Adaptive accuracy thresholds based on device type - more lenient for error-free experience
    this.maxAccuracyThreshold = this.isMobileDevice ? 200 : 2000; // Much more lenient thresholds
    this.ipFallbackThreshold = this.isMobileDevice ? 500 : 3000;
    
    // Enhanced location options
    this.locationAttempts = 0;
    this.maxLocationAttempts = 3;

    // Bind methods
    this.handlePositionUpdate = this.handlePositionUpdate.bind(this);
    this.handlePositionError = this.handlePositionError.bind(this);
  }

  // Initialize the service with token and callbacks
  initialize(token, callbacks = {}) {
    this.token = token;
    this.onLocationUpdate = callbacks.onLocationUpdate || (() => {});
    this.onError = callbacks.onError || (() => {});
    this.onPermissionChange = callbacks.onPermissionChange || (() => {});

    console.log('📍 LocationTrackingService initialized for', this.isMobileDevice ? 'mobile' : 'desktop');
  }

  // Check if geolocation is supported
  isSupported() {
    return 'geolocation' in navigator;
  }

  // Enhanced mobile device detection
  detectMobileDevice() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    
    // Check for mobile devices
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
    
    // Check for touch screen
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    // Check screen size and orientation
    const isSmallScreen = window.innerWidth <= 768 && window.innerHeight <= 1024;
    
    return isMobile || (hasTouch && isSmallScreen);
  }

  // Enhanced permission request with better user guidance
  async requestPermission() {
    if (!this.isSupported()) {
      throw new Error('Geolocation is not supported in this browser');
    }

    try {
      const result = await navigator.permissions.query({ name: 'geolocation' });
      console.log('📍 Current permission state:', result.state);

      // Listen for permission changes
      result.onchange = () => {
        console.log('📍 Permission state changed to:', result.state);
        this.onPermissionChange(result.state);
      };

      if (result.state === 'denied') {
        const deviceType = this.isMobileDevice ? 'mobile' : 'desktop';
        const instructions = this.isMobileDevice 
          ? 'Please enable location services in your browser settings and device settings.'
          : 'Please enable location services in your browser settings and ensure your device has location capabilities.';
        
        throw new Error(`Location permission denied. ${instructions}`);
      }

      // If permission is granted or prompt, try to get position with enhanced options
      if (result.state === 'granted' || result.state === 'prompt') {
        return new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              console.log('📍 Location permission granted with position:', position.coords);
              this.onPermissionChange('granted');
              resolve('granted');
            },
            (error) => {
              console.error('📍 Location permission error:', error);
              
              // Provide specific guidance based on error
              let errorMessage = 'Location access denied or unavailable';
              if (error.code === error.PERMISSION_DENIED) {
                errorMessage = this.isMobileDevice 
                  ? 'Location permission denied. Please enable location in browser and device settings.'
                  : 'Location permission denied. Please allow location access in your browser.';
              } else if (error.code === error.POSITION_UNAVAILABLE) {
                errorMessage = this.isMobileDevice
                  ? 'Location unavailable. Please ensure GPS is enabled on your device.'
                  : 'Location unavailable. Please check your device location settings.';
              }
              
              this.onPermissionChange('denied');
              reject(new Error(errorMessage));
            },
            {
              timeout: 15000,
              enableHighAccuracy: true,
              maximumAge: 0
            }
          );
        });
      }

      return result.state;
    } catch (error) {
      console.error('📍 Permission check error:', error);
      throw error;
    }
  }

  // Enhanced location tracking start with WiFi positioning and sensor data
  async startTracking(options = {}) {
    if (!this.isSupported()) {
      throw new Error('Geolocation is not supported in this browser');
    }

    if (!this.token) {
      throw new Error('Authentication token required');
    }

    try {
      // Request permission first
      await this.requestPermission();

      // Get initial position with enhanced accuracy methods
      const initialPosition = await this.getEnhancedAccuracyPosition();
      console.log('📍 Initial position accuracy:', initialPosition.coords.accuracy);

      // Get user preferences from backend
      const preferences = await this.getTrackingPreferences();

      this.updateInterval = (preferences.update_interval || 30) * 1000;
      const backgroundTracking = preferences.background_tracking;
      const highRiskOnly = preferences.high_risk_alerts_only;

      console.log('📍 Starting enhanced location tracking with preferences:', {
        updateInterval: this.updateInterval,
        backgroundTracking,
        highRiskOnly,
        deviceType: this.isMobileDevice ? 'mobile' : 'desktop'
      });

      // Enhanced watch options with maximum accuracy settings
      const watchOptions = {
        enableHighAccuracy: true,
        timeout: this.isMobileDevice ? 30000 : 45000, // Longer timeout for desktop
        maximumAge: this.isMobileDevice ? 10000 : 30000, // Fresher data for mobile
        ...options
      };

      this.watchId = navigator.geolocation.watchPosition(
        this.handlePositionUpdate,
        this.handlePositionError,
        watchOptions
      );

      this.isTracking = true;
      this.locationAttempts = 0;

      console.log('📍 Enhanced location tracking started, watchId:', this.watchId);

      return {
        success: true,
        watchId: this.watchId,
        initialAccuracy: initialPosition.coords.accuracy
      };

    } catch (error) {
      console.error('📍 Failed to start tracking:', error);
      this.onError(error);
      throw error;
    }
  }

  // Enhanced accuracy position with multiple strategies
  async getEnhancedAccuracyPosition() {
    const strategies = [
      // Strategy 1: High accuracy GPS
      () => this.getHighAccuracyPosition(),

      // Strategy 2: WiFi positioning (Mozilla Location Services)
      async () => {
        console.log('📍 Attempting WiFi-based positioning...');
        try {
          const wifiPosition = await this.getWiFiPosition();
          if (wifiPosition) return wifiPosition;
        } catch (error) {
          console.warn('📍 WiFi positioning failed:', error);
        }
        throw new Error('WiFi positioning unavailable');
      },

      // Strategy 3: Enhanced GPS with different settings
      async () => {
        console.log('📍 Attempting enhanced GPS settings...');
        return new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(
            resolve,
            reject,
            {
              enableHighAccuracy: true,
              timeout: 20000,
              maximumAge: 10000
            }
          );
        });
      }
    ];

    for (const strategy of strategies) {
      try {
        const position = await strategy();
        const accuracy = position.coords.accuracy;
        console.log(`📍 Strategy successful, accuracy: ${accuracy}m`);
        return position;
      } catch (error) {
        console.warn('📍 Strategy failed:', error.message);
        continue;
      }
    }

    throw new Error('All positioning strategies failed');
  }

  // Get high accuracy position with multiple attempts
  async getHighAccuracyPosition() {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const maxAttempts = 3;

      const tryGetPosition = () => {
        attempts++;

        navigator.geolocation.getCurrentPosition(
          (position) => {
            const accuracy = position.coords.accuracy;
            console.log(`📍 Position attempt ${attempts}, accuracy: ${accuracy}m`);

            // Accept position if accuracy is good enough
            if (accuracy <= this.maxAccuracyThreshold || attempts >= maxAttempts) {
              resolve(position);
            } else {
              // Try again with different options
              setTimeout(tryGetPosition, 2000);
            }
          },
          (error) => {
            if (attempts >= maxAttempts) {
              reject(error);
            } else {
              setTimeout(tryGetPosition, 2000);
            }
          },
          {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
          }
        );
      };

      tryGetPosition();
    });
  }

  // WiFi-based positioning using Mozilla Location Services
  async getWiFiPosition() {
    try {
      // Get WiFi access points (if available)
      if (!navigator || !navigator.geolocation) {
        throw new Error('Geolocation not available');
      }

      // Use Mozilla Location Services API
      const response = await fetch('https://location.services.mozilla.com/v1/geolocate?key=test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          wifiAccessPoints: [
            // Note: In a real implementation, you'd scan for actual WiFi networks
            // This is a placeholder for demonstration
          ]
        })
      });

      if (!response.ok) {
        throw new Error(`Mozilla Location Services error: ${response.status}`);
      }

      const data = await response.json();

      return {
        coords: {
          latitude: data.location.lat,
          longitude: data.location.lng,
          accuracy: data.accuracy || 1000
        },
        timestamp: Date.now()
      };

    } catch (error) {
      console.warn('📍 WiFi positioning error:', error);
      throw error;
    }
  }

  // Stop location tracking
  stopTracking() {
    if (this.watchId) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
      this.isTracking = false;
      this.lastPosition = null;
      this.locationAttempts = 0;
      console.log('📍 Location tracking stopped');
    }
  }

  // Updated handlePositionUpdate in LocationTrackingService.js
async handlePositionUpdate(position) {
  try {
    const { latitude, longitude, accuracy } = position.coords;
    const timestamp = position.timestamp;

    // Store the GPS position for fallback use
    this.lastGPSPosition = { latitude, longitude, accuracy };

    console.log('📍 New position update:', {
      latitude,
      longitude,
      accuracy,
      device: this.isMobileDevice ? 'mobile' : 'desktop'
    });

    // Validate coordinates are within Pakistan bounds
    if (!this.isValidPakistanCoordinates(latitude, longitude)) {
      console.warn('📍 Invalid coordinates detected (outside Pakistan):', { latitude, longitude });
      this.onError(new Error('Location appears to be outside Pakistan. Please check your location settings.'));
      return;
    }

    // Enhanced accuracy validation - be more lenient
    if (accuracy > this.maxAccuracyThreshold) {
      console.warn(`📍 Accuracy ${accuracy}m exceeds threshold ${this.maxAccuracyThreshold}m`);
      
      // Try to get better accuracy
      if (this.locationAttempts < this.maxLocationAttempts) {
        this.locationAttempts++;
        console.log(`📍 Attempting to get better accuracy (attempt ${this.locationAttempts})`);
        
        try {
          const betterPosition = await this.getHighAccuracyPosition();
          await this.processLocationUpdate(
            betterPosition.coords.latitude,
            betterPosition.coords.longitude,
            betterPosition.coords.accuracy,
            betterPosition.timestamp,
            'gps_enhanced'
          );
          return;
        } catch (retryError) {
          console.warn('📍 Failed to get better accuracy:', retryError);
        }
      }

      // If still poor accuracy, use IP fallback for desktop but don't block the update
      if (!this.isMobileDevice && accuracy > this.ipFallbackThreshold) {
        console.log('📍 Desktop device with poor accuracy, attempting IP fallback');
        // Don't await this - let it run in background while we process GPS data
        this.attemptIPFallback(timestamp);
      }

      // Log accuracy info but don't throw error - just process the location
      console.log(`📍 Location accuracy: ${Math.round(accuracy)}m (${this.isMobileDevice ? 'mobile' : 'desktop'})`);
    }

    // Always process the GPS location regardless of accuracy
    await this.processLocationUpdate(latitude, longitude, accuracy, timestamp, 
      accuracy <= this.maxAccuracyThreshold ? 'gps_high_accuracy' : 'gps_low_accuracy');

  } catch (error) {
    console.error('📍 Error handling position update:', error);
    this.onError(error);
  }
}


async attemptIPFallback(timestamp) {
  try {
    console.log('📍 Attempting IP-based geolocation fallback...');
    const ipLocation = await this.getLocationFromIP();

    if (ipLocation && this.isValidPakistanCoordinates(ipLocation.latitude, ipLocation.longitude)) {
      console.log('📍 Using IP-based location:', ipLocation);

      // Silent IP fallback - no error thrown, just process the location
      await this.processLocationUpdate(
        ipLocation.latitude,
        ipLocation.longitude,
        ipLocation.accuracy,
        timestamp,
        'ip_fallback'
      );
    } else {
      console.warn('📍 IP geolocation returned invalid coordinates or failed');
      // Process the original GPS location even with poor accuracy - no error thrown
      if (this.lastGPSPosition) {
        await this.processLocationUpdate(
          this.lastGPSPosition.latitude,
          this.lastGPSPosition.longitude,
          this.lastGPSPosition.accuracy,
          timestamp,
          'gps_low_accuracy_fallback'
        );
      }
    }
  } catch (ipError) {
    console.error('📍 IP geolocation fallback failed:', ipError);
    // Process the original GPS location even with poor accuracy - no error thrown
    if (this.lastGPSPosition) {
      await this.processLocationUpdate(
        this.lastGPSPosition.latitude,
        this.lastGPSPosition.longitude,
        this.lastGPSPosition.accuracy,
        timestamp,
        'gps_low_accuracy_fallback'
      );
    }
  }
}

  // Handle position error with enhanced guidance
  handlePositionError(error) {
    console.error('📍 Geolocation error:', error);

    let errorMessage = 'Unable to access your location';
    let userGuidance = '';

    switch (error.code) {
      case error.PERMISSION_DENIED:
        errorMessage = 'Location access denied';
        userGuidance = this.isMobileDevice
          ? 'Please enable location in your browser settings and device settings, then refresh the page.'
          : 'Please allow location access in your browser settings and ensure your device has location capabilities.';
        this.onPermissionChange('denied');
        break;
        
      case error.POSITION_UNAVAILABLE:
        errorMessage = 'Location information unavailable';
        userGuidance = this.isMobileDevice
          ? 'Please ensure GPS is enabled on your device and you have a clear view of the sky.'
          : 'Please check your device location settings and ensure you are connected to the internet.';
        break;
        
      case error.TIMEOUT:
        errorMessage = 'Location request timed out';
        userGuidance = 'Please ensure you have a stable internet connection and try again.';
        break;
    }

    const fullErrorMessage = userGuidance ? `${errorMessage}. ${userGuidance}` : errorMessage;
    this.onError(new Error(fullErrorMessage));
  }

  // Send location data to backend
  async sendLocationToBackend(locationData) {
    if (!this.token) {
      throw new Error('No authentication token');
    }

    try {
      const response = await fetch('/api/location/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify(locationData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update location');
      }

      const result = await response.json();
      console.log('📍 Location sent to backend:', result);

      return result;
    } catch (error) {
      console.error('📍 Failed to send location to backend:', error);
      throw error;
    }
  }

  // Get tracking preferences from backend
  async getTrackingPreferences() {
    try {
      const response = await fetch('/api/location/preferences', {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to get preferences');
      }

      return await response.json();
    } catch (error) {
      console.warn('📍 Failed to get preferences, using defaults:', error);
      return {
        enabled: true,
        update_interval: 30,
        background_tracking: false,
        high_risk_alerts_only: false
      };
    }
  }

  // Enhanced IP location service in LocationTrackingService.js
async getLocationFromIP() {
  try {
    console.log('📍 Fetching location from backend IP geolocation endpoint...');

    const response = await fetch('/api/location/ip-geolocation', {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });

    if (!response.ok) {
      // Don't throw error, just log and return null
      console.warn('📍 Backend IP geolocation failed with status:', response.status);
      return null;
    }

    const data = await response.json();

    // Validate the response data
    if (!data.latitude || !data.longitude) {
      console.warn('📍 Invalid IP geolocation response:', data);
      return null;
    }

    // Transform backend response to match expected format
    return {
      latitude: data.latitude,
      longitude: data.longitude,
      accuracy: data.accuracy || 5000,
      address: data.city ? `${data.city}, ${data.country}` : 'Unknown location',
      source: 'ip',
      service: data.source
    };

  } catch (error) {
    console.error('📍 Backend IP geolocation failed:', error);
    // Return null instead of throwing to allow graceful fallback
    return null;
  }
}

  async processLocationUpdate(latitude, longitude, accuracy, timestamp, locationSource = 'gps') {
    try {
      // Check if position has changed significantly
      if (this.lastPosition) {
        const distance = this.calculateDistance(
          this.lastPosition.latitude,
          this.lastPosition.longitude,
          latitude,
          longitude
        );

        // Skip update if distance is too small and time interval hasn't passed
        if (distance < this.minDistance) {
          const timeSinceLastUpdate = Date.now() - (this.lastUpdate || 0);
          if (timeSinceLastUpdate < this.updateInterval) {
            console.log('📍 Skipping update - minimal movement');
            return;
          }
        }

        // Enhanced jump detection - only for GPS sources, more lenient for IP fallback
        if (locationSource.startsWith('gps')) {
          const timeDiff = (Date.now() - (this.lastUpdate || 0)) / 1000 / 60; // minutes
          if (timeDiff > 0 && timeDiff < 60) { // Only check if within last hour
            const speedKmh = (distance / 1000) / (timeDiff / 60); // km/h
            // More realistic threshold: 200 km/h (highway speeds + margin)
            if (speedKmh > 200) {
              console.warn('📍 Suspicious location jump detected:', { distance, speedKmh, timeDiff, source: locationSource });
              this.onError(new Error('Unusual location change detected. Please verify your location.'));
              return;
            }
          }
        }
      }

      console.log('📍 Processing location update:', { 
        latitude, 
        longitude, 
        accuracy, 
        source: locationSource,
        device: this.isMobileDevice ? 'mobile' : 'desktop'
      });

      // Get address from coordinates
      let address = null;
      try {
        address = await this.reverseGeocode(latitude, longitude);
      } catch (error) {
        console.warn('📍 Reverse geocoding failed:', error);
      }

      // Send location to backend with enhanced information
      const locationData = {
        latitude,
        longitude,
        accuracy,
        address,
        location_source: locationSource,
        device_type: this.isMobileDevice ? 'mobile' : 'desktop',
        timestamp: new Date(timestamp).toISOString()
      };

      await this.sendLocationToBackend(locationData);

      // Update state
      this.lastPosition = { latitude, longitude, accuracy };
      this.lastUpdate = Date.now();
      this.locationAttempts = 0; // Reset attempts on successful update

      // Notify callback with enhanced data
      this.onLocationUpdate({
        position: locationData,
        address,
        timestamp,
        source: locationSource,
        accuracy: accuracy,
        deviceType: this.isMobileDevice ? 'mobile' : 'desktop'
      });

    } catch (error) {
      console.error('📍 Error processing location update:', error);
      this.onError(error);
    }
  }

  // Enhanced reverse geocoding with multiple free services fallback
  async reverseGeocode(lat, lng) {
    const services = [
      // Primary: Photon (Komoot) - unlimited free, fast and reliable
      async () => {
        const response = await fetch(
          `https://photon.komoot.io/reverse?lat=${lat}&lon=${lng}&lang=en`
        );
        if (!response.ok) throw new Error(`Photon error: ${response.status}`);
        const data = await response.json();

        // Transform Photon response to standardized format
        if (data.features && data.features[0]) {
          const feature = data.features[0];
          return {
            address: {
              road: feature.properties.street,
              neighbourhood: feature.properties.neighbourhood,
              suburb: feature.properties.suburb,
              city: feature.properties.city,
              state: feature.properties.state,
              country: feature.properties.country
            },
            source: 'photon'
          };
        }
        throw new Error('No Photon results');
      },

      // Fallback 1: Nominatim (OpenStreetMap) - unlimited free
      async () => {
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1&accept-language=en&extratags=1`
        );
        if (!response.ok) throw new Error(`Nominatim error: ${response.status}`);
        const data = await response.json();

        if (data && data.address) {
          return {
            address: data.address,
            source: 'nominatim'
          };
        }
        throw new Error('No Nominatim results');
      },

      // Fallback 2: Geoapify (free tier: 3000/day) - high quality but limited
      async () => {
        const response = await fetch(
          `https://api.geoapify.com/v1/geocode/reverse?lat=${lat}&lon=${lng}&apiKey=demo&format=json`
        );
        if (!response.ok) throw new Error(`Geoapify error: ${response.status}`);
        const data = await response.json();

        // Transform Geoapify response
        if (data.results && data.results[0]) {
          const result = data.results[0];
          return {
            address: {
              road: result.street,
              neighbourhood: result.neighbourhood,
              suburb: result.suburb,
              city: result.city,
              state: result.state,
              country: result.country
            },
            source: 'geoapify'
          };
        }
        throw new Error('No Geoapify results');
      }
    ];

    for (const service of services) {
      try {
        const data = await service();

        if (data && data.address) {
          const addr = data.address;
          const addressParts = [];

          // Enhanced address building logic with Lahore-specific prioritization
          if (addr.road) addressParts.push(addr.road);
          if (addr.neighbourhood) addressParts.push(addr.neighbourhood);
          if (addr.suburb) addressParts.push(addr.suburb);
          if (addr.city_district) addressParts.push(addr.city_district);
          if (addr.city) addressParts.push(addr.city);
          if (addr.state) addressParts.push(addr.state);

          const address = addressParts.join(', ');
          console.log(`📍 Geocoding successful (${data.source}):`, address);
          return address || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        }
      } catch (error) {
        console.warn(`📍 Geocoding service failed:`, error.message);
        continue;
      }
    }

    // Final fallback
    console.warn('📍 All geocoding services failed, using coordinates');
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }

  // Calculate distance between two coordinates (Haversine formula)
  calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c; // Distance in meters
  }

  // Validate coordinates are within Pakistan bounds with Lahore focus
  isValidPakistanCoordinates(lat, lng) {
    // Pakistan approximate bounds with buffer
    const minLat = 23.0;  // Southern border
    const maxLat = 37.0;  // Northern border
    const minLng = 60.0;  // Western border
    const maxLng = 78.0;  // Eastern border

    // Lahore specific bounds for validation
    const lahoreMinLat = 31.25;
    const lahoreMaxLat = 31.75;
    const lahoreMinLng = 73.8;
    const lahoreMaxLng = 74.7;

    const isInPakistan = lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng;
    const isInLahore = lat >= lahoreMinLat && lat <= lahoreMaxLat && lng >= lahoreMinLng && lng <= lahoreMaxLng;

    if (!isInPakistan) {
      console.warn('📍 Coordinates outside Pakistan bounds:', { lat, lng });
      return false;
    }

    // Log if coordinates are in Lahore area
    if (isInLahore) {
      console.log('📍 Coordinates validated in Lahore area');
    }

    return true;
  }

  // Get current tracking status
  getStatus() {
    return {
      isTracking: this.isTracking,
      watchId: this.watchId,
      lastUpdate: this.lastUpdate,
      lastPosition: this.lastPosition,
      updateInterval: this.updateInterval,
      supported: this.isSupported(),
      isMobileDevice: this.isMobileDevice,
      maxAccuracyThreshold: this.maxAccuracyThreshold,
      locationAttempts: this.locationAttempts
    };
  }

  // Enhanced retry with multiple strategies
  async retryLocation(options = {}) {
    console.log('📍 Retrying location with enhanced options:', options);

    const retryOptions = {
      enableHighAccuracy: true,
      timeout: this.isMobileDevice ? 30000 : 45000,
      maximumAge: 0, // Force fresh location
      ...options
    };

    try {
      const position = await this.getHighAccuracyPosition();
      await this.handlePositionUpdate(position);
      return position;
    } catch (error) {
      console.error('📍 Enhanced retry failed:', error);
      throw error;
    }
  }

  // Cleanup
  destroy() {
    this.stopTracking();
    this.token = null;
    this.onLocationUpdate = null;
    this.onError = null;
    this.onPermissionChange = null;
    console.log('📍 LocationTrackingService destroyed');
  }
}

// Export singleton instance
const locationTrackingService = new LocationTrackingService();
export default locationTrackingService;
