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
      return await response.json();
    } catch (error) {
      console.error('Error fetching crimes:', error);
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
  }
};

export default apiService;
