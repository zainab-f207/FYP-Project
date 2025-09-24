const API_BASE_URL = 'http://127.0.0.1:8000';

export const apiService = {
  async getAreas() {
    try {
      console.log('Fetching areas from:', `${API_BASE_URL}/api/areas`);
      const response = await fetch(`${API_BASE_URL}/api/areas`);

      console.log('Areas response status:', response.status, response.statusText);

      if (!response.ok) {
        console.error('Areas response not OK:', response.status, response.statusText);
        throw new Error('Failed to fetch areas');
      }

      const data = await response.json();
      console.log('Areas API response data:', data);
      console.log('Areas array:', data.areas);
      console.log('Number of areas:', data.areas ? data.areas.length : 0);

      return data;
    } catch (error) {
      console.error('Error fetching areas:', error);
      return { areas: [] };
    }
  },

  async getCrimeTypes() {
    try {
      console.log('Fetching crime types from:', `${API_BASE_URL}/api/crime-types`);
      const response = await fetch(`${API_BASE_URL}/api/crime-types`);

      console.log('Crime types response status:', response.status, response.statusText);

      if (!response.ok) {
        console.error('Crime types response not OK:', response.status, response.statusText);
        throw new Error('Failed to fetch crime types');
      }

      const data = await response.json();
      console.log('Crime types API response data:', data);
      console.log('Crime types array:', data.crime_types);
      console.log('Number of crime types:', data.crime_types ? data.crime_types.length : 0);

      return data;
    } catch (error) {
      console.error('Error fetching crime types:', error);
      return { crime_types: [] };
    }
  },

  async getCrimes(filters = {}) {
    try {
      const params = new URLSearchParams();
      if (filters.crime_type) params.append('crime_type', filters.crime_type);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.limit) params.append('limit', filters.limit);

      const response = await fetch(`${API_BASE_URL}/api/crimes?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch crimes');
      }

      const data = await response.json();

      // Transform backend response to match frontend expectations
      // Backend returns: id, area, type, date, coordinates: [lat, lng], risk_level
      // Frontend expects: id, area, crime_type, date, latitude, longitude, risk_level, coordinates
      const transformedData = data
        .filter(crime => {
          // Check if coordinates are valid numbers (not null, undefined, or NaN)
          const coords = crime.coordinates;
          if (!Array.isArray(coords) || coords.length < 2) {
            console.warn(`Filtering out crime ${crime.id} - invalid coordinates array:`, coords);
            return false;
          }

          const lat = coords[0];
          const lng = coords[1];

          const isValidLat = lat !== null && lat !== undefined && !isNaN(lat) && isFinite(lat);
          const isValidLng = lng !== null && lng !== undefined && !isNaN(lng) && isFinite(lng);

          if (!isValidLat || !isValidLng) {
            console.warn(`Filtering out crime ${crime.id} - invalid coordinates: lat=${lat}, lng=${lng}`);
            return false;
          }

          return true;
        })
        .map(crime => ({
          id: crime.id,
          area: crime.area,
          crime_type: crime.type, // Backend uses 'type', frontend expects 'crime_type'
          date: crime.date,
          latitude: crime.coordinates[0], // Extract from coordinates array
          longitude: crime.coordinates[1], // Extract from coordinates array
          risk_level: crime.risk_level,
          coordinates: crime.coordinates // Keep coordinates array for compatibility
        }));

      console.log(`Filtered crimes: ${data.length} total, ${transformedData.length} with valid coordinates`);
      return transformedData;
    } catch (error) {
      console.error('Error fetching crimes:', error);
      return [];
    }
  },

  // New function specifically for fetching crimes by area (for map filtering)
  async getCrimesByArea(area, filters = {}) {
    try {
      const params = new URLSearchParams();
      if (area) params.append('area', area); // Use backend area filtering
      if (filters.crime_type) params.append('crime_type', filters.crime_type);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.limit) params.append('limit', filters.limit);

      console.log('Fetching crimes with area filter:', area);
      console.log('Full URL:', `${API_BASE_URL}/api/crimes?${params}`);

      const response = await fetch(`${API_BASE_URL}/api/crimes?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch crimes');
      }

      const data = await response.json();
      console.log('Area-filtered crimes response:', data);
      console.log('Number of crimes returned:', Array.isArray(data) ? data.length : 0);

      // Transform backend response and filter out crimes with invalid coordinates
      // Backend returns: id, area, type, date, coordinates: [lat, lng], risk_level
      // Frontend expects: id, area, crime_type, date, latitude, longitude, risk_level, coordinates
      const transformedData = data
        .filter(crime => {
          // Check if coordinates are valid numbers (not null, undefined, or NaN)
          const coords = crime.coordinates;
          if (!Array.isArray(coords) || coords.length < 2) {
            console.warn(`Filtering out crime ${crime.id} - invalid coordinates array:`, coords);
            return false;
          }

          const lat = coords[0];
          const lng = coords[1];

          const isValidLat = lat !== null && lat !== undefined && !isNaN(lat) && isFinite(lat);
          const isValidLng = lng !== null && lng !== undefined && !isNaN(lng) && isFinite(lng);

          if (!isValidLat || !isValidLng) {
            console.warn(`Filtering out crime ${crime.id} - invalid coordinates: lat=${lat}, lng=${lng}`);
            return false;
          }

          return true;
        })
        .map(crime => ({
          id: crime.id,
          area: crime.area,
          crime_type: crime.type, // Backend uses 'type', frontend expects 'crime_type'
          date: crime.date,
          latitude: crime.coordinates[0], // Extract from coordinates array
          longitude: crime.coordinates[1], // Extract from coordinates array
          risk_level: crime.risk_level,
          coordinates: crime.coordinates // Keep coordinates array for compatibility
        }));

      console.log(`Filtered area crimes: ${data.length} total, ${transformedData.length} with valid coordinates`);
      console.log('Transformed data sample:', transformedData.slice(0, 3));
      return transformedData;
    } catch (error) {
      console.error('Error fetching crimes by area:', error);
      return [];
    }
  },

  async predictRisk(area, crimeType, date = null) {
    try {
      const body = {
        area: area,
        crime_type: crimeType
      };
      if (date) {
        body.date = date;
      }

      const response = await fetch(`${API_BASE_URL}/api/predict-risk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('Failed to predict risk');
      }
      return await response.json();
    } catch (error) {
      console.error('Error predicting risk:', error);
      return null;
    }
  },

  // Authentication functions
  async register(userData) {
    try {
      console.log('Registering user:', userData);
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      console.log('Registration response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Registration failed:', response.status, errorData);
        throw new Error(errorData.detail || `Registration failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Registration successful:', data);
      return data;
    } catch (error) {
      console.error('Error during registration:', error);
      throw error;
    }
  },

  async login(credentials) {
    try {
      console.log('Logging in user:', credentials.username);
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      console.log('Login response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Login failed:', response.status, errorData);
        throw new Error(errorData.detail || `Login failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Login successful:', data);
      return data;
    } catch (error) {
      console.error('Error during login:', error);
      throw error;
    }
  },

  async getCurrentUser(token) {
    debugger
    try {
      console.log('Getting current user info');
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Get user response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Get user failed:', response.status, errorData);
        throw new Error(errorData.detail || `Get user failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Get user successful:', data);
      return data;
    } catch (error) {
      console.error('Error getting current user:', error);
      throw error;
    }
  },

  async updateProfile(profileData, token) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/update-profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(profileData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  },

  async uploadProfilePhoto(file, token) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/auth/upload-profile-photo`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to upload profile photo');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error uploading profile photo:', error);
      throw error;
    }
}

}

export default apiService;
