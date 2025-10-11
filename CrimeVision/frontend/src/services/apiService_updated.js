// Use relative paths to leverage Vite's proxy configuration
// This ensures API calls work both locally and through tunnels like ngrok
const API_BASE_URL = '';

console.log('apiService using relative paths (leveraging Vite proxy)');

const buildQueryString = (params = {}) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach(item => {
        if (item !== undefined && item !== null && item !== '') {
          searchParams.append(key, item);
        }
      });
      return;
    }

    if (value !== '') {
      searchParams.append(key, value);
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
};

const normalizeUser = (user) => ({
  id: user.id,
  username: user.username,
  firstName: user.first_name,
  lastName: user.last_name,
  email: user.email,
  role: user.role,
  permissions: user.permissions || [],
  homeArea: user.home_area,
  workArea: user.work_area,
  alertRadius: user.alert_radius,
  createdAt: user.created_at,
  activityLogs: user.activity_logs || [],
});

const normalizeAdmin = (admin) => ({
  id: admin.id,
  username: admin.username,
  firstName: admin.first_name,
  lastName: admin.last_name,
  email: admin.email,
  role: admin.role,
  department: admin.department,
  lastLogin: admin.last_login,
  permissions: admin.permissions || [],
});

const apiService = {
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

      return data.areas || [];
    } catch (error) {
      console.error('Error fetching areas:', error);
      return [];
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

      return data.crime_types || [];
    } catch (error) {
      console.error('Error fetching crime types:', error);
      return [];
    }
  },

  async getUsers(token, params = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/users${buildQueryString(params)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch users');
      }

      const data = await response.json();
      return {
        users: Array.isArray(data.users) ? data.users.map(normalizeUser) : [],
        total: data.total ?? 0,
        limit: data.limit ?? params.limit ?? 10,
        offset: data.offset ?? params.offset ?? 0,
      };
    } catch (error) {
      console.error('Error fetching users:', error);
      throw error;
    }
  },

  async bulkUserActions(token, action, userIds = []) {
    try {
      if (!Array.isArray(userIds) || userIds.length === 0) {
        throw new Error('No user IDs provided for bulk action');
      }

      const searchParams = new URLSearchParams();
      searchParams.append('action', action);
      userIds.forEach((id) => searchParams.append('user_ids', id));

      const response = await fetch(`${API_BASE_URL}/admin/user-bulk?${searchParams.toString()}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to perform bulk user action');
      }

      return await response.json();
    } catch (error) {
      console.error('Error performing bulk user action:', error);
      throw error;
    }
  },

  async updateUserPermissions(token, userId, permissions = []) {
    try {
      const searchParams = new URLSearchParams();
      searchParams.append('user_id', userId);
      permissions.forEach((permission) => searchParams.append('permissions', permission));

      const response = await fetch(`${API_BASE_URL}/admin/user-roles?${searchParams.toString()}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update user permissions');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating user permissions:', error);
      throw error;
    }
  },

  async getCrimes(filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/crimes${buildQueryString(filters)}`);
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
      const response = await fetch(`${API_BASE_URL}/api/crimes${buildQueryString({ ...filters, area })}`);
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
      console.log('Logging in user:', credentials.email);
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

  async verifyEmail(token) {
    try {
      console.log('Verifying email with token');
      const response = await fetch(`${API_BASE_URL}/auth/verify-email?token=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('Email verification response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Email verification failed:', response.status, errorData);
        throw new Error(errorData.detail || `Email verification failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Email verification successful:', data);
      return data;
    } catch (error) {
      console.error('Error during email verification:', error);
      throw error;
    }
  },

  async getCurrentUser(token) {
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
  },

  // Admin functions
  async registerAdmin(adminData, token) {
    try {
      console.log('Registering admin:', adminData);
      const response = await fetch(`${API_BASE_URL}/admin/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(adminData),
      });

      console.log('Admin registration response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Admin registration failed:', response.status, errorData);
        throw new Error(errorData.detail || `Admin registration failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Admin registration successful:', data);
      return data;
    } catch (error) {
      console.error('Error during admin registration:', error);
      throw error;
    }
  },

  async getAdmins(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/list${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Get admins response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Get admins failed:', response.status, errorData);
        throw new Error(errorData.detail || `Get admins failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Get admins successful:', data);
      return {
        admins: Array.isArray(data.admins) ? data.admins.map(normalizeAdmin) : [],
        total: data.total ?? data.admins?.length ?? 0,
        limit: data.limit ?? filters.limit ?? 10,
        offset: data.offset ?? filters.offset ?? 0,
      };
    } catch (error) {
      console.error('Error getting admins:', error);
      throw error;
    }
  },

  async getAdminStats(token) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/stats`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Get admin stats response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Get admin stats failed:', response.status, errorData);
        throw new Error(errorData.detail || `Get admin stats failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Get admin stats successful:', data);
      return {
        ...data,
        totalUsers: data.total_users,
        totalAdmins: data.total_admins,
        activeReports: data.active_reports,
        systemHealth: data.system_health,
        predictionsToday: data.predictions_today,
        preventedCrimes: data.prevented_crimes,
      };
    } catch (error) {
      console.error('Error getting admin stats:', error);
      throw error;
    }
  },

  async getAdminNotifications(token) {
    try {
      console.log('Fetching admin notifications');
      const response = await fetch(`${API_BASE_URL}/admin/notifications`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Get admin notifications response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Get admin notifications failed:', response.status, errorData);
        throw new Error(errorData.detail || `Get admin notifications failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Get admin notifications successful:', data);
      return Array.isArray(data.notifications)
        ? data.notifications.map((notification) => ({
            id: notification.id,
            type: notification.type,
            title: notification.title,
            message: notification.message,
            timestamp: notification.timestamp,
            urgent: notification.type === 'warning' || notification.type === 'error' || notification.urgent,
          }))
        : [];
    } catch (error) {
      console.error('Error getting admin notifications:', error);
      throw error;
    }
  },

  // Reporting functions for new endpoints
  async getCrimeSummaryReport(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/crime-summary${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch crime summary report');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching crime summary report:', error);
      throw error;
    }
  },

  async getUserActivityReport(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/user-activity${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch user activity report');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching user activity report:', error);
      throw error;
    }
  },

  async getSystemHealthReport(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/system-health${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch system health report');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching system health report:', error);
      throw error;
    }
  },

  async exportCrimeData(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/export-crime-data${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to export crime data');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `crime_data_export.${filters.format || 'json'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting crime data:', error);
      throw error;
    }
  },

  // Legacy functions (keeping for backward compatibility)
  async fetchReportData(token, reportType, startDate, endDate) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/analytics/time-series${buildQueryString({ reportType, startDate, endDate })}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch report data');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching report data:', error);
      throw error;
    }
  },

  async exportReport(token, reportType, startDate, endDate, format) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/export${buildQueryString({ reportType, startDate, endDate, format })}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to export report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportType}_${startDate}_to_${endDate}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting report:', error);
      throw error;
    }
  },

  // Reporting functions for ReportingDashboard
  async getReportHistory(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/history${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch report history');
      }

      const data = await response.json();
      return data.reports || [];
    } catch (error) {
      console.error('Error fetching report history:', error);
      return [];
    }
  },

  async getScheduledReports(token, filters = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/scheduled${buildQueryString(filters)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch scheduled reports');
      }

      const data = await response.json();
      return data.scheduled_reports || [];
    } catch (error) {
      console.error('Error fetching scheduled reports:', error);
      return [];
    }
  },

  async generateCustomReport(token, reportData) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(reportData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate custom report');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error generating custom report:', error);
      throw error;
    }
  },

  async scheduleReport(token, scheduleData) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(scheduleData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to schedule report');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error scheduling report:', error);
      throw error;
    }
  },

  async downloadReport(token, reportId) {
    try {
      // First get report metadata to determine the format
      const reports = await this.getReportHistory(token, { id: reportId });
      const report = reports.find(r => r.id === reportId);

      if (!report) {
        throw new Error('Report not found');
      }

      const format = report.format || 'pdf';
      const extension = format.toLowerCase();

      const response = await fetch(`${API_BASE_URL}/admin/reports/download/${reportId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to download report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading report:', error);
      throw error;
    }
  },

  // Password reset functions
  async forgotPassword(email) {
    try {
      console.log('Sending forgot password request for:', email);
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      console.log('Forgot password response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Forgot password failed:', response.status, errorData);
        throw new Error(errorData.detail || `Forgot password failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Forgot password successful:', data);
      return data;
    } catch (error) {
      console.error('Error during forgot password:', error);
      throw error;
    }
  },

  async resetPassword(token, newPassword) {
    try {
      console.log('Resetting password with token');
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, new_password: newPassword }),
      });

      console.log('Reset password response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Reset password failed:', response.status, errorData);
        throw new Error(errorData.detail || `Reset password failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Reset password successful:', data);
      return data;
    } catch (error) {
      console.error('Error during reset password:', error);
      throw error;
    }
  },

  // Two-Factor Authentication functions
  async setup2FA(token) {
    try {
      console.log('Setting up 2FA');
      const response = await fetch(`${API_BASE_URL}/auth/2fa/setup`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Setup 2FA response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Setup 2FA failed:', response.status, errorData);
        throw new Error(errorData.detail || `Setup 2FA failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Setup 2FA successful:', data);
      return data;
    } catch (error) {
      console.error('Error during setup 2FA:', error);
      throw error;
    }
  },

  async verify2FA(token, code) {
    try {
      console.log('Enabling 2FA with code');
      const response = await fetch(`${API_BASE_URL}/auth/2fa/enable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ code }),
      });

      console.log('Enable 2FA response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Enable 2FA failed:', response.status, errorData);
        throw new Error(errorData.detail || `Enable 2FA failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Enable 2FA successful:', data);
      return data;
    } catch (error) {
      console.error('Error during enable 2FA:', error);
      throw error;
    }
  },

  async disable2FA(token) {
    try {
      console.log('Disabling 2FA');
      const response = await fetch(`${API_BASE_URL}/auth/2fa/disable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Disable 2FA response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Disable 2FA failed:', response.status, errorData);
        throw new Error(errorData.detail || `Disable 2FA failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Disable 2FA successful:', data);
      return data;
    } catch (error) {
      console.error('Error during disable 2FA:', error);
      throw error;
    }
  }
}

export { apiService };
export default apiService;
