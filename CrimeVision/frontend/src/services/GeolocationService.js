// GeolocationService.js

const HIGH_ACCURACY_SETTINGS = {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 30000
};

const STANDARD_ACCURACY_SETTINGS = {
  enableHighAccuracy: false,
  timeout: 20000,
  maximumAge: 60000
};

class GeolocationService {
  static async getHighAccuracyLocation() {
    if (!navigator.geolocation) {
      throw new Error('Geolocation not supported');
    }

    try {
      // Try high accuracy first
      const position = await this.getCurrentPositionPromise(HIGH_ACCURACY_SETTINGS);
      return this.formatPosition(position, 'high');
    } catch (error) {
      console.warn('High accuracy GPS failed, trying standard GPS:', error);
      
      // Fallback to standard GPS
      try {
        const position = await this.getCurrentPositionPromise(STANDARD_ACCURACY_SETTINGS);
        return this.formatPosition(position, 'standard');
      } catch (fallbackError) {
        console.error('All GPS methods failed:', fallbackError);
        throw fallbackError;
      }
    }
  }

  static startLiveTracking(onLocationUpdate, onError) {
    if (!navigator.geolocation) {
      onError(new Error('Geolocation not supported'));
      return null;
    }

    console.log('🚗 Starting optimized live tracking...');
    
    const settings = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000
    };

    return navigator.geolocation.watchPosition(
      (position) => {
        const locationData = this.formatPosition(position);
        onLocationUpdate(locationData);
      },
      (error) => {
        console.error('Live tracking error:', error);
        if (onError) onError(error);
      },
      settings
    );
  }

  static stopLiveTracking(watchId) {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      console.log('🛑 Stopped live tracking');
    }
  }

  static formatPosition(position, accuracyLevel = 'unknown') {
    const { latitude, longitude, accuracy, speed, heading } = position.coords;
    
    // Determine accuracy level based on GPS accuracy
    let finalAccuracyLevel = accuracyLevel;
    if (accuracyLevel === 'unknown') {
      if (accuracy < 10) finalAccuracyLevel = 'high';
      else if (accuracy < 50) finalAccuracyLevel = 'medium';
      else finalAccuracyLevel = 'low';
    }

    return {
      lat: latitude,
      lng: longitude,
      accuracy: accuracy,
      accuracyLevel: finalAccuracyLevel,
      speed: speed || 0,
      heading: heading || 0,
      timestamp: position.timestamp
    };
  }

  static getCurrentPositionPromise(settings) {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, settings);
    });
  }
}

export default GeolocationService;
