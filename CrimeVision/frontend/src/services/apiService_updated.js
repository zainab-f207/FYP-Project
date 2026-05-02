// Enhanced API_BASE_URL detection with multiple fallback strategies
let API_BASE_URL;
let API_BASE_URL_FALLBACKS = [];

// Priority order for API base URL detection
const envApi = import.meta?.env?.VITE_API_BASE_URL;
const PRODUCTION_API_URL = 'https://safevision-backend-ye2i.onrender.com';

if (envApi) {
  API_BASE_URL = envApi;
  console.log('Using environment variable API_BASE_URL:', API_BASE_URL);
} else {
  const host = window.location.hostname;
  const protocol = window.location.protocol;
  const isLocalhost = host === 'localhost' || host === '127.0.0.1';
  const isLocalNetwork = host.startsWith('192.168.') || host.startsWith('10.') || host.startsWith('172.');
  // Public hosting providers — appending :8000 to these never works.
  const isProductionHost =
    host.endsWith('.vercel.app') ||
    host.endsWith('.netlify.app') ||
    host.endsWith('.pages.dev') ||
    host.endsWith('.onrender.com');
  const hasDevPort = !!window.location.port;

  if (isProductionHost) {
    // Env var didn't reach this build. Use the deployed backend URL so the
    // app still works even without VITE_API_BASE_URL configured.
    API_BASE_URL = PRODUCTION_API_URL;
    API_BASE_URL_FALLBACKS = [PRODUCTION_API_URL];
    console.log('Production host detected, using:', API_BASE_URL);
  } else {
    API_BASE_URL_FALLBACKS = [
      `${protocol}//${host}:8000`,
      `${protocol}//localhost:8000`,
      `${protocol}//127.0.0.1:8000`,
      `${protocol}//192.168.0.101:8000`,
      `${protocol}//192.168.1.101:8000`,
      `${protocol}//10.0.0.101:8000`,
    ];
    API_BASE_URL = API_BASE_URL_FALLBACKS[0];

    console.log('Dynamic API_BASE_URL detection:', {
      primary: API_BASE_URL,
      fallbacks: API_BASE_URL_FALLBACKS.slice(1),
      hostname: host,
      isLocalhost,
      isLocalNetwork,
      hasDevPort
    });
  }
}

// Test connectivity and switch to working URL
async function testApiConnectivity(url, timeout = 3000) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(`${url}/health`, {
      method: 'GET',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' }
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    console.warn(`API connectivity test failed for ${url}:`, error.message);
    return false;
  }
}

// Auto-detect working API URL on initialization
async function initializeApiBaseUrl() {
  console.log('🔍 Testing API connectivity...');

  // Test primary URL first
  if (await testApiConnectivity(API_BASE_URL)) {
    console.log('✅ Primary API URL working:', API_BASE_URL);
    return;
  }

  // Test fallbacks
  for (const fallbackUrl of API_BASE_URL_FALLBACKS.slice(1)) {
    console.log('🔄 Testing fallback URL:', fallbackUrl);
    if (await testApiConnectivity(fallbackUrl)) {
      console.log('✅ Found working API URL:', fallbackUrl);
      API_BASE_URL = fallbackUrl;
      return;
    }
  }

  console.warn('❌ No working API URL found, using primary URL as fallback');
}

// Initialize API connectivity detection
if (typeof window !== 'undefined') {
  // Run connectivity test after page load
  window.addEventListener('load', () => {
    initializeApiBaseUrl();
  });
}

console.log('apiService initialized with API_BASE_URL =', API_BASE_URL);

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
  firstName: admin.first_name || '',
  lastName: admin.last_name || '',
  name: admin.name || `${admin.first_name || ''} ${admin.last_name || ''}`.trim(),
  email: admin.email,
  role: admin.role,
  department: admin.department,
  phone: admin.phone,
  address: admin.address,
  lastLogin: admin.last_login,
  createdAt: admin.created_at,
  status: admin.status || 'active',
  permissions: admin.permissions || [],
});

const apiService = {
  // Add API_BASE_URL as a property so it can be imported
  API_BASE_URL,

  async post(endpoint, data = {}, token = null) {
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      console.log(`🔄 API POST: ${API_BASE_URL}${endpoint}`, data);
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed: ${response.statusText}`);
      }

      const responseData = await response.json();
      console.log(`✅ API POST Success: ${endpoint}`, responseData);
      return responseData;
    } catch (error) {
      console.error(`❌ API POST Error: ${endpoint}`, error);
      throw error;
    }
  },

  async put(endpoint, data = {}, token = null) {
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      console.log(`🔄 API PUT: ${API_BASE_URL}${endpoint}`, data);
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed: ${response.statusText}`);
      }

      const responseData = await response.json();
      console.log(`✅ API PUT Success: ${endpoint}`, responseData);
      return responseData;
    } catch (error) {
      console.error(`❌ API PUT Error: ${endpoint}`, error);
      throw error;
    }
  },

  async updateAdmin(token, adminId, data) {
    return this.put(`/admin/${adminId}`, data, token);
  },

  async updateUser(token, userId, data) {
    return this.put(`/admin/users/${userId}`, data, token);
  },

  async validateToken(token) {
    try {
      console.log('🔐 Validating token...');
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        throw new Error('Token expired');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Token validation failed');
      }

      const userData = await response.json();
      console.log('✅ Token validation successful');
      return userData;
    } catch (error) {
      console.error('❌ Token validation error:', error);
      throw error;
    }
  },

  withAuthRetry: async (requestFn, token, maxRetries = 1) => {
    try {
      return await requestFn();
    } catch (error) {
      if ((error && error.message && error.message.includes('401')) && maxRetries > 0) {
        // Token might be expired, try to refresh
        console.log('Token might be expired, attempting refresh...');
        // You would implement token refresh logic here
        throw new Error('Authentication required');
      }
      throw error;
    }
  },

  // Generic GET method
  async get(endpoint, token = null) {
    const resolvedToken = token ||
      localStorage.getItem('SafeVision_token') ||
      sessionStorage.getItem('SafeVision_token');
    return this.withAuthRetry(async () => {
      try {
        const headers = {
          'Content-Type': 'application/json',
        };
        if (resolvedToken) {
          headers['Authorization'] = `Bearer ${resolvedToken}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'GET',
          headers,
        });

        if (response.status === 401) {
          throw new Error('Authentication required');
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Request failed: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        console.error('Error in GET request:', error);
        throw error;
      }
    }, resolvedToken);
  },

  async login(credentials) {
    try {
      console.log('🔐 Logging in user:', credentials.email);
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

        // Provide specific error messages
        if (response.status === 429) {
          // Rate limiting - account locked
          const retryAfter = response.headers.get('Retry-After');
          const err = new Error(errorData.detail || 'Too many login attempts. Please try again later.');
          err.status = 429;
          err.retryAfter = retryAfter ? parseInt(retryAfter) : null;
          throw err;
        } else if (response.status === 401) {
          // Include remaining attempts info if present in detail
          throw new Error(errorData.detail || 'Invalid email or password');
        } else if (response.status === 403) {
          throw new Error('Please verify your email address before logging in');
        } else if (response.status === 422) {
          throw new Error('Invalid input data');
        } else {
          throw new Error(errorData.detail || `Login failed: ${response.statusText}`);
        }
      }

      const data = await response.json();
      console.log('✅ Login successful, token received');

      // Handle requires_2fa_setup (admin without 2FA) - has access_token but needs setup
      if (data.requires_2fa_setup) {
        return data; // Pass through to AuthContext
      }

      // Handle mandatory email OTP for admin/superadmin
      if (data.requires_email_otp) {
        console.log('🔐 Email OTP required for admin/superadmin login');
        return data; // Pass through to AuthContext
      }

      if (!data.access_token) {
        throw new Error('No access token received from server');
      }

      return data;
    } catch (error) {
      console.error('❌ Error during login:', error);
      throw error;
    }
  },

  async verifyLoginOtp(userId, otpCode) {
    try {
      console.log('🔐 Verifying login OTP for user:', userId);
      const response = await fetch(`${API_BASE_URL}/auth/verify-login-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, otp_code: otpCode }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'OTP verification failed');
      }

      const data = await response.json();
      console.log('✅ OTP verified successfully');
      return data;
    } catch (error) {
      console.error('❌ Error verifying OTP:', error);
      throw error;
    }
  },

  async resendLoginOtp(userId) {
    try {
      console.log('🔐 Resending login OTP for user:', userId);
      const response = await fetch(`${API_BASE_URL}/auth/resend-login-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to resend OTP');
      }

      return await response.json();
    } catch (error) {
      console.error('❌ Error resending OTP:', error);
      throw error;
    }
  },

  async forceChangePassword(token, newPassword, confirmPassword) {
    try {
      console.log('🔐 Force changing password');
      const response = await fetch(`${API_BASE_URL}/auth/force-change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ new_password: newPassword, confirm_password: confirmPassword }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to change password');
      }

      return await response.json();
    } catch (error) {
      console.error('❌ Error force changing password:', error);
      throw error;
    }
  },

  async forgotPassword(email) {
    try {
      console.log('🔐 Requesting password reset for:', email);
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to send password reset email');
      }

      console.log('✅ Password reset email sent');
      return data;
    } catch (error) {
      console.error('❌ Error during forgot password:', error);
      throw error;
    }
  },

  async resetPassword(token, newPassword) {
    try {
      console.log('🔐 Resetting password with token');
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, new_password: newPassword }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to reset password');
      }

      console.log('✅ Password reset successful');
      return data;
    } catch (error) {
      console.error('❌ Error during password reset:', error);
      throw error;
    }
  },


  // Add these methods to the apiService object in apiService_updated.js

  // async googleLogin(credential, twoFactorCode = null) {
  //     try {
  //       console.log('🔐 Logging in with Google credential');
  //       const response = await fetch(`${API_BASE_URL}/auth/google-login`, {
  //         method: 'POST',
  //         headers: {
  //           'Content-Type': 'application/json',
  //         },
  //         body: JSON.stringify({
  //           credential: credential,
  //           two_factor_code: twoFactorCode
  //         }),
  //       });

  //       console.log('Google login response status:', response.status, response.statusText);

  //       const data = await response.json();

  //       // Handle special cases first (these return 200 but no tokens)
  //       if (data.requires_verification) {
  //         return {
  //           requires_verification: true,
  //           message: data.message,
  //           user_info: data.user_info
  //         };
  //       }

  //       if (data.requires_2fa) {
  //         return {
  //           requires_2fa: true,
  //           message: data.message,
  //           user_info: data.user_info
  //         };
  //       }

  //       if (!response.ok) {
  //         console.error('Google login failed:', response.status, data);

  //         if (response.status === 401) {
  //           throw new Error('Invalid Google credential');
  //         } else if (response.status === 403) {
  //           throw new Error('Please verify your email address before logging in');
  //         } else if (response.status === 422) {
  //           throw new Error('Invalid input data');
  //         } else {
  //           throw new Error(data.detail || `Google login failed: ${response.statusText}`);
  //         }
  //       }

  //       console.log('✅ Google login successful, token received');

  //       if (!data.access_token) {
  //         throw new Error('No access token received from server');
  //       }

  //       return {
  //         success: true,
  //         access_token: data.access_token,
  //         refresh_token: data.refresh_token,
  //         username: data.username
  //       };
  //     } catch (error) {
  //       console.error('❌ Error during Google login:', error);
  //       throw error;
  //     }
  //   },


  async googleLogin(credential, twoFactorCode = null) {
    try {
      console.log('🔐 apiService: Google login started');
      console.log('🔐 apiService: API_BASE_URL:', API_BASE_URL);
      console.log('🔐 apiService: Credential received (first 50 chars):', credential ? credential.substring(0, 50) : 'null');

      const payload = { credential };
      if (twoFactorCode) {
        payload.two_factor_code = twoFactorCode;
      }

      console.log('🔐 apiService: Sending request to', `${API_BASE_URL}/auth/google-login`);

      const response = await fetch(`${API_BASE_URL}/auth/google-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      console.log('🔐 apiService: Google login response status:', response.status, response.statusText);

      let data; let rawText = '';
      try {
        rawText = await response.text();
        data = rawText ? JSON.parse(rawText) : {};
        console.log('🔐 apiService: Response data:', data);
      } catch (jsonError) {
        console.error('❌ apiService: Failed to parse response JSON:', jsonError, 'Raw:', rawText);
        data = {};
      }

      // Handle special cases first (these return 200 but no tokens)
      if (data && data.requires_verification) {
        console.log('🔐 apiService: User requires verification');
        return {
          requires_verification: true,
          message: data.message,
          user_info: data.user_info
        };
      }

      if (data && data.requires_2fa) {
        console.log('🔐 apiService: User requires 2FA');
        return {
          requires_2fa: true,
          message: data.message,
          user_info: data.user_info
        };
      }

      // Handle case where API returns requiresRegistration in a 200 OK response
      if (data && (data.requiresRegistration || data.requires_registration)) {
        console.log('🔐 apiService: User must register before Google sign-in');
        return {
          requiresRegistration: true,
          message: data.message,
          user_info: data.user_info
        };
      }

      if (!response.ok) {
        console.error('❌ apiService: Google login response not OK - status:', response.status);
        console.error('❌ apiService: Error data:', data);

        const detail = (data && (data.detail || data.message || data.error)) || '';
        const lower = String(detail || rawText || response.statusText).toLowerCase();

        // Explicitly detect unregistered user cases and signal UI to require registration
        if (response.status === 404 || lower.includes('not found') || lower.includes('no account') || lower.includes('not registered') || lower.includes('does not exist')) {
          return { requiresRegistration: true, error: detail || 'Account not found. Please sign up first.' };
        }

        if (response.status === 401) {
          throw new Error('Invalid Google credential');
        } else if (response.status === 403) {
          throw new Error('Please verify your email address before logging in');
        } else if (response.status === 422) {
          throw new Error('Invalid input data');
        } else {
          throw new Error(detail || `Google login failed: ${response.statusText}`);
        }
      }

      console.log('✅ apiService: Google login response OK');

      if (!data || !data.access_token) {
        console.warn('⚠️ apiService: No access token in response:', data);
        throw new Error('No access token received from server');
      }

      console.log('✅ apiService: Google login successful, returning tokens');

      return {
        success: true,
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        username: data.username,
        is_new_user: data.is_new_user
      };
    } catch (error) {
      console.error('❌ apiService: Error during Google login:', error);
      console.error('❌ apiService: Error type:', error.constructor.name);
      console.error('❌ apiService: Error message:', error.message);
      throw error;
    }
  },
  async googleRegister(userData, credential, twoFactorCode = null) {
    try {
      console.log('🔐 [DEBUG] Starting Google register...');

      // Decode Google credential to extract email
      let googleEmail = null;
      try {
        const payload = JSON.parse(atob(credential.split('.')[1]));
        googleEmail = payload.email;
        console.log('📧 [DEBUG] Extracted email from Google credential:', googleEmail);
      } catch (decodeError) {
        console.error('❌ [DEBUG] Failed to decode Google credential:', decodeError);
        throw new Error('Invalid Google credential format');
      }

      if (!googleEmail) {
        throw new Error('Email not found in Google credential');
      }

      const requestData = {
        first_name: userData.firstName || "",
        last_name: userData.lastName || "",
        email: googleEmail, // Use email from Google credential
        home_area: userData.homeArea || "",
        work_area: userData.workArea || "",
        phone_number: userData.phoneNumber || "",
        alert_radius: userData.alertRadius || 5,
        credential: credential,
        two_factor_code: twoFactorCode,
        profile_picture: userData.profilePicture || null
      };

      console.log('📤 [DEBUG] Full request data:', requestData);

      const response = await fetch(`${API_BASE_URL}/auth/google-register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      console.log('📨 [DEBUG] Response status:', response.status, response.statusText);

      // Always try to parse the response body
      let data;
      const responseText = await response.text();
      console.log('📨 [DEBUG] Raw response text:', responseText);

      if (!response.ok) {
        // Handle error responses
        let errorMessage = `Registration failed with status ${response.status}`;

        if (responseText) {
          try {
            const errorData = JSON.parse(responseText);
            console.error('❌ [DEBUG] Server error details:', errorData);

            // Extract meaningful error message from various possible formats
            if (errorData.detail) {
              errorMessage = errorData.detail;
            } else if (errorData.message) {
              errorMessage = errorData.message;
            } else if (errorData.error) {
              errorMessage = errorData.error;
            } else if (typeof errorData === 'string') {
              errorMessage = errorData;
            } else if (Array.isArray(errorData) && errorData.length > 0) {
              // Handle validation errors array
              errorMessage = errorData.map(err =>
                typeof err === 'string' ? err : err.message || err.detail || JSON.stringify(err)
              ).join(', ');
            }
          } catch (parseError) {
            console.error('❌ [DEBUG] Failed to parse error response:', parseError);
            // Use raw text if JSON parsing fails
            errorMessage = responseText || errorMessage;
          }
        }

        throw new Error(errorMessage);
      }

      // Handle successful responses
      if (!responseText || responseText.trim() === '') {
        console.error('❌ [DEBUG] Empty response body from server');
        throw new Error('Server returned empty response');
      }

      try {
        data = JSON.parse(responseText);
        console.log('✅ [DEBUG] Parsed response data:', data);
      } catch (parseError) {
        console.error('❌ [DEBUG] Failed to parse JSON response:', parseError);
        throw new Error('Server returned invalid JSON response');
      }

      return data;

    } catch (error) {
      console.error('❌ [DEBUG] Error during Google register:', error);
      // Ensure we always throw a string error message
      throw new Error(typeof error.message === 'string' ? error.message : 'Google registration failed');
    }
  },



  async getGoogleClientId() {
    try {
      console.log('Getting Google Client ID from server');
      const response = await fetch(`${API_BASE_URL}/auth/google-client-id`);

      if (!response.ok) {
        throw new Error('Failed to get Google Client ID');
      }

      const data = await response.json();
      return data.client_id;
    } catch (error) {
      console.error('Error getting Google Client ID:', error);
      throw error;
    }
  },

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

  async searchAreasAndCrimeTypes(query) {
    try {
      console.log('Searching areas and crime types from:', `${API_BASE_URL}/api/search?q=${encodeURIComponent(query)}`);
      const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query)}`);

      console.log('Search response status:', response.status, response.statusText);

      if (!response.ok) {
        console.error('Search response not OK:', response.status, response.statusText);
        throw new Error('Failed to search');
      }

      const data = await response.json();
      console.log('Search API response data:', data);
      console.log('Search results:', data.results);
      console.log('Number of results:', data.results ? data.results.length : 0);

      return data.results || [];
    } catch (error) {
      console.error('Error searching:', error);
      return [];
    }
  },


  // Add to your apiService methods
  async getAreaSafetyScore(area) {
    try {
      console.log('Fetching safety score for area:', area);
      const response = await fetch(`${API_BASE_URL}/api/areas/${area}/safety-score`);

      if (!response.ok) {
        throw new Error(`Failed to fetch safety score: ${response.status}`);
      }

      const data = await response.json();
      console.log('Safety score response:', data);
      return data;
    } catch (error) {
      console.error('Error fetching safety score:', error);
      throw error;
    }
  },

  async getAreaCoordinates(area) {
    try {
      console.log('Fetching coordinates for area:', area);

      // Clean up area name for better matching
      const cleanArea = area.trim();
      // Try multiple query formats to increase success rate
      const queries = [
        `${cleanArea}, Lahore, Pakistan`,
        `${cleanArea}, Lahore`,
        `${cleanArea} Lahore`
      ];

      for (const query of queries) {
        try {
          console.log(`Trying geocoding query: ${query}`);
          const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);

          if (response.ok) {
            const data = await response.json();
            if (data && data.length > 0) {
              const coords = {
                lat: parseFloat(data[0].lat),
                lng: parseFloat(data[0].lon)
              };
              console.log('✅ Coordinates found:', coords);
              return { coordinates: coords };
            }
          }
        } catch (e) {
          console.warn(`Geocoding failed for ${query}`, e);
        }
        // Small delay to be nice to the API
        await new Promise(r => setTimeout(r, 200));
      }

      throw new Error('No coordinates found after trying multiple queries');
    } catch (error) {
      console.error('Error fetching area coordinates:', error);
      throw error; // Propagate error so UI knows it failed (no fake fallback)
    }
  },

  async getMultipleAreaSafetyScores(areas) {
    try {
      console.log('Fetching safety scores for multiple areas:', areas);
      const searchParams = new URLSearchParams();
      areas.forEach(area => searchParams.append('areas', area));

      const response = await fetch(`${API_BASE_URL}/api/areas/safety-scores?${searchParams.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch safety scores: ${response.status}`);
      }

      const data = await response.json();
      console.log('Multiple safety scores response:', data);
      return data.safety_scores || {};
    } catch (error) {
      console.error('Error fetching multiple safety scores:', error);
      throw error;
    }
  },

  async subscribeToAlerts(token, subscriptionData) {
    try {
      console.log('🔔 Subscribing to alerts:', subscriptionData);

      const updatedSubscriptionData = {
        ...subscriptionData,
      };

      // Backend route is /api/alerts/community/subscribe via alerts router.
      const response = await fetch(`${API_BASE_URL}/api/alerts/community/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(updatedSubscriptionData),
      });

      console.log('📡 Subscribe alerts response status:', response.status, response.statusText);

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status} ${response.statusText}`;

        try {
          const errorText = await response.text();
          console.error('📄 Raw error response:', errorText);

          if (errorText) {
            const errorData = JSON.parse(errorText);
            errorMessage = errorData.detail || errorData.message || errorMessage;
          }
        } catch (parseError) {
          console.error('❌ Error parsing error response:', parseError);
          // Use default error message if parsing fails
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('✅ Subscribe alerts successful:', data);
      return data;
    } catch (error) {
      console.error('❌ Error subscribing to alerts:', error);

      // Enhanced error messages for common issues
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Network error: Cannot connect to server. Please check your internet connection and try again.');
      }

      if (error.message.includes('401') || error.message.includes('Invalid token')) {
        throw new Error('Authentication failed. Please log in again.');
      }

      if (error.message.includes('500')) {
        throw new Error('Server error. Please try again later.');
      }

      throw error;
    }
  },

  async getCrimeTrends(token, { start_date, end_date, area } = {}) {
    try {
      const params = {};
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;
      if (area && area !== 'all') params.area = area;

      const crimes = await this.get(`/api/crimes${buildQueryString(params)}`, token);

      // Aggregate crimes by date
      const trendsMap = {};
      (crimes || []).forEach(crime => {
        // Handle different date formats if necessary, assuming ISO string or YYYY-MM-DD
        let date = crime.crime_date;
        if (date.includes('T')) {
          date = date.split('T')[0];
        }

        if (!trendsMap[date]) {
          trendsMap[date] = { actual: 0, predicted: 0 };
        }
        trendsMap[date].actual++;
      });

      // Convert to array and sort
      const trends = Object.entries(trendsMap).map(([date, counts]) => ({
        date,
        actual: counts.actual,
        predicted: counts.predicted // Placeholder as we don’t have historical predictions stored in this way yet
      })).sort((a, b) => new Date(a.date) - new Date(b.date));

      return trends;
    } catch (error) {
      console.error('Error fetching crime trends:', error);
      throw error;
    }
  },

  async getReportHistory(token) {
    return this.get('/admin/reports/history', token);
  },

  async getScheduledReports(token) {
    return this.get('/admin/reports/scheduled', token);
  },

  async generateCustomReport(token, data) {
    return this.post('/admin/reports/generate', data, token);
  },

  async scheduleReport(token, data) {
    return this.post('/admin/reports/schedule', data, token);
  },

  async downloadReport(token, reportId) {
    // For download, we might need to handle blob response
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reports/${reportId}/download`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${reportId}.pdf`; // Adjust extension based on content type if needed
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading report:', error);
      throw error;
    }
  },

  // Admin specific methods
  // SuperAdmin specific stats with more comprehensive data
  async getSuperAdminStats(token) {
    try {
      // Get comprehensive system stats for SuperAdmin
      const [statsResponse, crimesResponse, usersResponse, adminsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/stats`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }),
        this.get('/api/crimes', token),
        this.getAllUsers(token).catch(() => []), // Fallback to empty array if fails
        this.getAllAdmins(token).catch(() => [])  // Fallback to empty array if fails
      ]);

      console.log('Get SuperAdmin stats response status:', statsResponse.status, statsResponse.statusText);

      const baseStats = statsResponse.ok ? await statsResponse.json() : {};
      const crimes = crimesResponse || [];
      const users = usersResponse || [];
      const admins = adminsResponse || [];

      // Calculate enhanced stats for SuperAdmin
      const last30Days = new Date();
      last30Days.setDate(last30Days.getDate() - 30);

      const recentCrimes = crimes.filter(crime =>
        new Date(crime.crime_date || crime.created_at) >= last30Days
      );

      return {
        ...baseStats,
        total_users:   baseStats.total_users   || 0,
        total_admins:  baseStats.total_admins  || 0,
        total_crimes:  baseStats.total_crimes  || 0,
        recent_crimes: baseStats.recent_crimes || recentCrimes.length || 0,
        crimes_by_risk:  baseStats.crimes_by_risk  || {},
        crimes_by_area:  baseStats.crimes_by_area  || {},
      };
    } catch (error) {
      console.error('Error getting SuperAdmin stats:', error);
      // Return basic fallback stats
      return {
        total_users: 0,
        total_admins: 0,
        total_crimes: 0,
        recent_crimes: 0,
        system_health: 85,
        predictions_today: 0,
        prevented_crimes: 0,
        active_alerts: 0
      };
    }
  },

  async getAdminStats(token) {
    try {
      // Get all crimes to calculate real stats
      const [statsResponse, crimesResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/stats`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }),
        this.get('/api/crimes', token)
      ]);

      console.log('Get admin stats response status:', statsResponse.status, statsResponse.statusText);

      if (!statsResponse.ok) {
        const errorData = await statsResponse.json().catch(() => ({}));
        console.error('Get admin stats failed:', statsResponse.status, errorData);
        throw new Error(errorData.detail || `Get admin stats failed: ${statsResponse.statusText}`);
      }

      const data = await statsResponse.json();
      const crimes = crimesResponse || [];

      // Calculate high-risk areas (areas with crime count > average)
      const areaStats = {};
      crimes.forEach(crime => {
        const area = crime.crime_area || 'Unknown';
        areaStats[area] = (areaStats[area] || 0) + 1;
      });

      const avgCrimes = Object.values(areaStats).reduce((a, b) => a + b, 0) / Object.keys(areaStats).length || 0;
      const highRiskAreas = Object.values(areaStats).filter(count => count > avgCrimes).length;

      // Calculate prevented crimes (crimes with status 'prevented' or similar)
      const preventedCrimes = crimes.filter(crime =>
        crime.status === 'prevented' ||
        crime.status === 'resolved' ||
        crime.notes?.toLowerCase().includes('prevented')
      ).length;

      // Calculate prediction accuracy based on actual vs predicted crimes
      const last30Days = crimes.filter(crime => {
        const crimeDate = new Date(crime.crime_date);
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        return crimeDate >= thirtyDaysAgo;
      });

      // Mock prediction accuracy (in real scenario, compare with ML predictions)
      const predictionAccuracy = Math.min(95, 85 + (preventedCrimes / Math.max(last30Days.length, 1)) * 10);

      console.log('Get admin stats successful:', data);
      return {
        ...data,
        total_crimes: crimes.length,
        totalUsers: data.total_users,
        totalAdmins: data.total_admins,
        activeReports: data.active_reports || crimes.filter(c => c.status === 'active').length,
        systemHealth: 98.7,
        high_risk_areas: highRiskAreas,
        prevented_crimes: preventedCrimes,
        prediction_accuracy: predictionAccuracy.toFixed(1),
        predictionsToday: last30Days.length,
      };
    } catch (error) {
      console.error('Error getting admin stats:', error);
      throw error;
    }
  },

  async getUniqueAreas(token) {
    try {
      const crimes = await this.get('/api/crimes', token);
      const areas = [...new Set(crimes.map(crime => crime.crime_area).filter(Boolean))];
      return areas.sort();
    } catch (error) {
      console.error('Error getting unique areas:', error);
      return [];
    }
  },

  async getAdminNotifications(token) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/notifications`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch admin notifications');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting admin notifications:', error);
      throw error;
    }
  },

  async checkLocationForAlerts(token, locationData) {
    try {
      console.log('Checking location for alerts via location tracking:', locationData);
      const response = await fetch(`${API_BASE_URL}/api/location/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(locationData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Location alert check failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Location alert check successful:', data);
      return data;
    } catch (error) {
      console.error('Error checking location for alerts:', error);
      throw error;
    }
  },

  async getAlertStatus(token) {
    try {
      console.log('Getting alert status');
      const response = await fetch(`${API_BASE_URL}/api/alerts/status`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Get alert status failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Alert status successful:', data);
      return data;
    } catch (error) {
      console.error('Error getting alert status:', error);
      throw error;
    }
  },

  async unsubscribeFromAlerts(token) {
    try {
      if (!token) {
        throw new Error('Missing auth token for unsubscribe');
      }
      console.log('Unsubscribing from alerts via POST /api/alerts/unsubscribe');
      const response = await fetch(`${API_BASE_URL}/api/alerts/unsubscribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('Unsubscribe alerts response status:', response.status, response.statusText);

      // Idempotent handling: if backend returns an error when no active subscriptions exist,
      // treat it as already-unsubscribed success and normalize the result.
      if (!response.ok) {
        let detail = '';
        try {
          const text = await response.text();
          try {
            const parsed = text ? JSON.parse(text) : {};
            detail = parsed.detail || parsed.message || text || response.statusText;
          } catch {
            detail = text || response.statusText;
          }
        } catch (_) {
          // ignore
        }

        const lower = String(detail).toLowerCase();
        const idempotent =
          response.status === 404 ||
          response.status === 409 ||
          response.status === 422 ||
          response.status === 500 && (lower.includes('failed to unsubscribe') || lower.includes('no') || lower.includes('not found') || lower.includes('no active'));

        if (idempotent) {
          console.warn('Unsubscribe returned non-OK but will be treated as success (idempotent):', detail);
          return { message: 'Already unsubscribed', status: 'ok' };
        }

        console.error('Unsubscribe alerts failed (non-idempotent):', response.status, detail);
        throw new Error(detail || `Unsubscribe alerts failed: ${response.statusText}`);
      }

      const data = await response.json().catch(() => ({ message: 'Unsubscribed' }));
      console.log('Unsubscribe alerts successful:', data);
      return data;
    } catch (error) {
      console.error('Error unsubscribing from alerts:', error);
      throw error;
    }
  },
  async getDetailedSafetyScore(area, days = 90) {
    try {
      console.log('Fetching detailed safety score for area:', area, 'days:', days);
      const response = await fetch(`${API_BASE_URL}/api/areas/${area}/safety-score/detailed?days=${days}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch detailed safety score: ${response.status}`);
      }

      const data = await response.json();
      console.log('Detailed safety score response:', data);
      return data;
    } catch (error) {
      console.error('Error fetching detailed safety score:', error);
      throw error;
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

  async bulkAdminActions(token, action, adminIds = []) {
    try {
      if (!Array.isArray(adminIds) || adminIds.length === 0) {
        throw new Error('No admin IDs provided for bulk action');
      }

      const searchParams = new URLSearchParams();
      searchParams.append('action', action);
      adminIds.forEach((id) => searchParams.append('admin_ids', id));

      const response = await fetch(`${API_BASE_URL}/admin/admin-bulk?${searchParams.toString()}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to perform bulk admin action');
      }

      return await response.json();
    } catch (error) {
      console.error('Error performing bulk admin action:', error);
      throw error;
    }
  },

  async getPublicSettings() {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/public-settings`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        console.warn('Failed to fetch public settings, using defaults');
        return null;
      }

      return await response.json();
    } catch (error) {
      console.warn('Error fetching public settings:', error);
      return null;
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
          area_urdu: crime.area_urdu || null,
          area_translit: crime.area_translit || null,
          crime_type: crime.type, // Backend uses 'type', frontend expects 'crime_type'
          date: crime.date,
          crime_time: crime.crime_time || null,
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
          area_urdu: crime.area_urdu || null,
          area_translit: crime.area_translit || null,
          crime_type: crime.type, // Backend uses 'type', frontend expects 'crime_type'
          date: crime.date,
          crime_time: crime.crime_time || null,
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

  async predictRisk(area, crimeType, date = null, time = null) {
    try {
      const body = {
        area: area,
        crime_type: crimeType
      };
      if (date) {
        body.date = date;
      }
      if (time) {
        body.time = time;
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
  // In your apiService_updated.js, update these functions:

  async getAreaAnalytics(area) {
    try {
      const data = await this.get(`/api/areas/${area}/analytics`);
      return data;
    } catch (error) {
      console.error('Error fetching area analytics:', error);
      throw error;
    }
  },

  async getAreaSafetyProfile(area, months = 12, options = {}) {
    try {
      const paramsObj = { area, months };
      if (options?.crimeType) {
        paramsObj.crime_type = options.crimeType;
      }
      if (options?.date) {
        paramsObj.date = options.date;
      }
      if (options?.visitTime) {
        paramsObj.visit_time = options.visitTime;
      }
      if (typeof options?.lat === 'number' && typeof options?.lng === 'number') {
        paramsObj.lat = options.lat;
        paramsObj.lng = options.lng;
      }
      if (typeof options?.radiusKm === 'number') {
        paramsObj.radius_km = options.radiusKm;
      }
      const params = new URLSearchParams(paramsObj).toString();
      const data = await this.get(`/api/crimes/area-safety-profile?${params}`);
      return data;
    } catch (error) {
      console.error('Error fetching area safety profile:', error);
      throw error;
    }
  },

  async getIntelligenceDashboard() {
    try {
      const data = await this.get('/api/crimes/intelligence-dashboard');
      return data;
    } catch (error) {
      console.error('Error fetching intelligence dashboard:', error);
      throw error;
    }
  },

  async triggerRetrain(token) {
    try {
      const data = await this.post('/api/crimes/model/trigger-retrain', {}, token);
      return data;
    } catch (error) {
      console.error('Error triggering model retrain:', error);
      throw error;
    }
  },

  async getAreaDetails(area) {
    try {
      const data = await this.get(`/api/areas/${area}/details`);
      return data;
    } catch (error) {
      console.error('Error fetching area details:', error);
      throw error;
    }
  },

  async getHeatmapData(area) {
    try {
      const data = await this.get(`/api/areas/${area}/heatmap`);
      return data;
    } catch (error) {
      console.error('Error fetching heatmap data:', error);
      throw error;
    }
  },

  async getAreaComparison(area) {
    try {
      const data = await this.get(`/api/areas/${area}/comparison`);
      return data;
    } catch (error) {
      console.error('Error fetching area comparison:', error);
      throw error;
    }
  },

  // Aggregated crime trends (daily) with a simple moving-average based prediction
  async getCrimeTrends(token, { start_date, end_date, area } = {}) {
    try {
      const params = {};
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;
      if (area && area !== 'all') params.area = area;

      const crimes = await this.get(`/api/crimes${buildQueryString(params)}`, token);

      // Build date range array (inclusive)
      const start = new Date(start_date);
      const end = new Date(end_date);
      const dates = [];
      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        // Clone date
        dates.push(new Date(d));
      }

      // Count crimes per date (backend returns crime_date in YYYY-MM-DD or similar)
      const counts = {};
      (crimes || []).forEach((c) => {
        const dt = c.date || c.crime_date || c.crimeDate || c.created_at;
        if (!dt) return;
        const key = dt.split('T')[0]; // YYYY-MM-DD
        counts[key] = (counts[key] || 0) + 1;
      });

      // Build result with moving-average predictions (7-day)
      const result = dates.map((d, idx) => {
        const iso = d.toISOString().split('T')[0];
        const label = d.toLocaleString('en-US', { month: 'short', day: '2-digit' });
        const actual = counts[iso] || 0;

        // compute moving average of previous 7 days for prediction
        let sum = 0;
        let n = 0;
        for (let k = 1; k <= 7; k++) {
          const prev = new Date(d);
          prev.setDate(prev.getDate() - k);
          const prevIso = prev.toISOString().split('T')[0];
          if (counts[prevIso] !== undefined) {
            sum += counts[prevIso];
            n++;
          }
        }
        const predicted = n > 0 ? Math.round(sum / n) : actual;

        return { date: label, actual, predicted };
      });

      return result;
    } catch (error) {
      console.error('Error fetching crime trends:', error);
      // Re-throw so caller can fallback if needed
      throw error;
    }
  },

  // Derive predictive analytics: patterns and heatmap from raw crime records
  async getPredictiveAnalytics(token, { start_date, end_date } = {}) {
    try {
      const params = {};
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;

      const crimes = await this.get(`/api/crimes${buildQueryString(params)}`, token);

      // Patterns: aggregate by hour (if available) and day_of_week
      const patternMap = {}; // key: `${hour}_${dow}` => count
      const heatmap = Array.from({ length: 7 }, () => Array.from({ length: 24 }, () => 0));

      (crimes || []).forEach((c) => {
        const dtRaw = c.date || c.crime_date || c.created_at;
        let dt = null;
        if (dtRaw) {
          dt = new Date(dtRaw);
        }

        const dow = dt ? dt.getDay() : Math.floor(Math.random() * 7); // 0-6
        const hour = dt ? dt.getHours() : Math.floor(Math.random() * 24);

        heatmap[dow][hour] = (heatmap[dow][hour] || 0) + 1;
        const key = `${hour}_${dow}`;
        patternMap[key] = (patternMap[key] || 0) + 1;
      });

      const patterns = Object.entries(patternMap).map(([k, v]) => {
        const [hour, dow] = k.split('_').map(Number);
        return { hour, day_of_week: dow, intensity: v };
      });

      // Normalize heatmap to 0-100 scale by percentage of max
      const max = heatmap.flat().reduce((m, x) => Math.max(m, x || 0), 0) || 1;
      const normalized = heatmap.map((row) => row.map((value) => Math.round((value / max) * 100)));

      return { patterns, risk_heatmap: normalized };
    } catch (error) {
      console.error('Error fetching predictive analytics:', error);
      throw error;
    }
  },

  // Area analysis built from crime-summary report
  async getAreaAnalysis(token, { start_date, end_date } = {}) {
    try {
      const params = {};
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;

      const data = await this.get(`/api/reports/crime-summary${buildQueryString(params)}`, token);

      const areasRaw = data.area_distribution || [];
      // Convert to frontend-expected structure: { name, crime_count, risk_level }
      const counts = areasRaw.map(a => ({ name: a.area, crime_count: a.count }));

      // Assign risk levels by quantiles (top 33% High, middle 34% Medium, rest Low)
      const sorted = [...counts].sort((a, b) => b.crime_count - a.crime_count);
      const total = sorted.length;
      const highCut = Math.ceil(total * 0.33);
      const medCut = Math.ceil(total * 0.66);

      const areas = sorted.map((a, idx) => ({
        name: a.name,
        crime_count: a.crime_count,
        risk_level: idx < highCut ? 'High' : idx < medCut ? 'Medium' : 'Low'
      }));

      return { areas };
    } catch (error) {
      console.error('Error fetching area analysis:', error);
      throw error;
    }
  },
  async register(userData) {
    try {
      // Normalize incoming user keys so backend always receives snake_case
      const payload = {
        first_name: userData.first_name || userData.firstName || userData.first || undefined,
        last_name: userData.last_name || userData.lastName || userData.last || undefined,
        email: userData.email || userData.email_address || undefined,
        password: userData.password || userData.pass || undefined,
        home_area: userData.home_area || userData.homeArea || userData.home || undefined,
        profile_picture: userData.profile_picture || userData.profilePicture || undefined,
        username: userData.username || userData.generatedUsername || userData.handle || undefined,
      };

      // Remove undefined keys
      Object.keys(payload).forEach((k) => payload[k] === undefined && delete payload[k]);

      console.log('Registering user (normalized payload):', payload);
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
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

  async getCurrentUser(token) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        throw new Error('Invalid token - Please login again');
      }

      if (response.status === 403) {
        throw new Error('Access forbidden');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Get user failed: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.username || !data.email) {
        throw new Error('Invalid user data received from server');
      }

      return data;
    } catch (error) {
      // Re-throw with original message; callers decide whether to log
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
  },

  // Patrol request function
  async requestPatrol(token, locationData) {
    try {
      console.log('Requesting patrol assistance:', locationData);
      const response = await fetch(`${API_BASE_URL}/api/patrol-request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          latitude: locationData.lat,
          longitude: locationData.lng,
          timestamp: new Date().toISOString(),
          urgency: 'medium', // Can be expanded to allow user selection
          description: 'User requested patrol assistance via mobile app'
        }),
      });

      console.log('Patrol request response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Patrol request failed:', response.status, errorData);
        throw new Error(errorData.detail || `Patrol request failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Patrol request successful:', data);
      return data;
    } catch (error) {
      console.error('Error requesting patrol:', error);
      throw error;
    }
  },


  // Community API functions
  async getCommunityStats() {
    try {
      console.log('Fetching community stats');
      const response = await fetch(`${API_BASE_URL}/api/community/stats`);

      console.log('Community stats response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Community stats failed:', response.status, errorData);
        throw new Error(errorData.detail || `Community stats failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Community stats successful:', data);
      return data.stats || {};
    } catch (error) {
      console.error('Error fetching community stats:', error);
      return {};
    }
  },


  async getCommunityAlerts(filters = {}) {
    try {
      console.log('Fetching community alerts:', filters);
      const response = await fetch(`${API_BASE_URL}/api/community/alerts${buildQueryString(filters)}`);

      console.log('Community alerts response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Community alerts failed:', response.status, errorData);
        throw new Error(errorData.detail || `Community alerts failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Community alerts successful:', data);
      return data.alerts || [];
    } catch (error) {
      console.error('Error fetching community alerts:', error);
      return [];
    }
  },






  async markAlertAsRead(token, alertId) {
    try {
      console.log('Marking alert as read:', alertId);
      const response = await fetch(`${API_BASE_URL}/api/auth/me/alerts/${alertId}/read`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to mark alert as read');
      }

      return await response.json();
    } catch (error) {
      console.error('Error marking alert as read:', error);
      throw error;
    }
  },

  async markAllAlertsAsRead(token) {
    try {
      console.log('Marking all alerts as read');
      const response = await fetch(`${API_BASE_URL}/api/auth/me/alerts/read-all`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to mark all alerts as read');
      }

      return await response.json();
    } catch (error) {
      console.error('Error marking all alerts as read:', error);
      throw error;
    }
  },



  async analyzeRouteSafety(routeData) {
    try {
      const response = await fetch(`${API_BASE_URL}/analyze_route_safety`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(routeData),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();
      return data; // example: { overall_score: 82, alerts: [...] }
    } catch (error) {
      console.error("Error in analyzeRouteSafety:", error);
      throw error;
    }
  },

  async analyzeRouteSafetyAI(routePoints, date = null) {
    try {
      console.log('🤖 Calling AI route safety analysis with', routePoints.length, 'points');
      const response = await fetch(`${API_BASE_URL}/api/crimes/analyze-route-safety-ai`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          route_points: routePoints,
          date: date
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI route safety analysis failed: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ AI route safety analysis successful:', data);
      return data; // { overall_score, safety_level, point_predictions, alerts, summary }
    } catch (error) {
      console.error("Error in analyzeRouteSafetyAI:", error);
      throw error;
    }
  },

  // Add this to your apiService in apiService_updated.js
  async logEmergencyCall(token, emergencyData) {
    try {
      console.log('Logging emergency call:', emergencyData);
      const response = await fetch(`${API_BASE_URL}/api/emergency-call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(emergencyData),
      });

      console.log('Emergency call response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Emergency call logging failed:', response.status, errorData);
        throw new Error(errorData.detail || `Emergency call logging failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Emergency call logged successfully:', data);
      return data;
    } catch (error) {
      console.error('Error logging emergency call:', error);
      throw error;
    }
  },

  // Add this to your apiService methods
  async logEmergencyCallPublic(emergencyData) {
    try {
      console.log('Logging public emergency call:', emergencyData);
      const response = await fetch(`${API_BASE_URL}/api/emergency-call/public`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(emergencyData),
      });

      console.log('Public emergency call response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Public emergency call logging failed:', response.status, errorData);
        throw new Error(errorData.detail || `Public emergency call logging failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Public emergency call logged successfully:', data);
      return data;
    } catch (error) {
      console.error('Error logging public emergency call:', error);
      throw error;
    }
  },
  // Make sure this method exists for emergency stats
  async getEmergencyStats() {
    try {
      console.log('Fetching emergency stats');
      const response = await fetch(`${API_BASE_URL}/api/emergency-stats`);

      console.log('Emergency stats response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Emergency stats failed:', response.status, errorData);
        throw new Error(errorData.detail || `Emergency stats failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Emergency stats successful:', data);
      return data;
    } catch (error) {
      console.error('Error fetching emergency stats:', error);
      throw error;
    }
  },

  // User stats and dashboard functions
  // User stats and dashboard functions - UPDATED WITH CORRECT ENDPOINTS
  // In apiService_updated.js, update these functions:

  // getUserStats was refactored below
  
  async getRecentActivity(token) {
    try {
      const data = await this.get('/api/auth/me/activity', token);
      return data;
    } catch (error) {
      console.error('Error fetching recent activity:', error);
      throw error;
    }
  },

  // Add this method to your apiService
  async testAlertSystem(token) {
    try {
      console.log('Testing alert system...');
      const response = await fetch(`${API_BASE_URL}/api/test/alert-system`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Alert system test failed');
      }

      const data = await response.json();
      console.log('Alert system test successful:', data);
      return data;
    } catch (error) {
      console.error('Error testing alert system:', error);
      throw error;
    }
  },


  // Add to your apiService_updated.js
  async subscribeToBrowserNotifications(token, subscriptionData) {
    try {
      console.log('🌐 Subscribing to browser notifications');
      const response = await fetch(`${API_BASE_URL}/api/alerts/browser-notifications/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(subscriptionData),
      });

      if (!response.ok) {
        throw new Error('Failed to subscribe to browser notifications');
      }

      return await response.json();
    } catch (error) {
      console.error('Error subscribing to browser notifications:', error);
      throw error;
    }
  },


  // In your apiService_updated.js - Update the setup function
  async setupBrowserPushNotifications() {
    try {
      console.log('🌐 Starting browser push notification setup...');

      // Import the push notification service
      const pushNotificationService = (await import('./push-notification.js')).default;

      // Try to fetch the VAPID public key from server and pass it to the push service
      let vapidPublicKey = null;
      try {
        const resp = await fetch(`${API_BASE_URL}/api/alerts/vapid-public-key`);
        if (resp.ok) {
          const data = await resp.json();
          vapidPublicKey = data.publicKey;
        } else {
          console.warn('⚠️ Failed to fetch VAPID public key from server:', resp.status);
        }
      } catch (err) {
        console.warn('⚠️ Error fetching VAPID public key:', err);
      }

      const initialized = await pushNotificationService.initialize(vapidPublicKey);
      if (!initialized) {
        throw new Error('Push notification service initialization failed');
      }

      // Subscribe to push notifications
      console.log('📱 Creating push subscription...');
      const subscriptionData = await pushNotificationService.subscribe();

      console.log('📤 Registering subscription with server...');
      await this.subscribeToBrowserNotifications(this.token, subscriptionData);

      console.log('✅ Browser push notifications setup completed successfully');

      // Test the notification
      await pushNotificationService.testNotification();
      return true;

    } catch (error) {
      console.error('❌ Browser push setup error:', error);
      throw new Error(`Browser notifications setup failed: ${error.message}`);
    }
  },

  async getBrowserNotifications(token, limit = 50, offset = 0) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/alerts/browser-notifications?limit=${limit}&offset=${offset}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get browser notifications');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting browser notifications:', error);
      throw error;
    }
  },

  async markBrowserNotificationRead(token, notificationId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/alerts/browser-notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to mark notification as read');
      }

      return await response.json();
    } catch (error) {
      console.error('Error marking notification as read:', error);
      throw error;
    }
  },

  async markAllBrowserNotificationsRead(token) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/alerts/browser-notifications/read-all`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to mark all notifications as read');
      }

      return await response.json();
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
      throw error;
    }
  },

  async getUserAlerts(token) {
    try {
      console.log('Fetching user alerts from:', `${API_BASE_URL}/api/auth/me/alerts`);
      const response = await fetch(`${API_BASE_URL}/api/auth/me/alerts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      console.log('User alerts response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Get user alerts failed:', response.status, errorData);
        throw new Error(errorData.detail || `Get user alerts failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('User alerts response data:', data);

      // Ensure we return an array of alerts
      const alerts = Array.isArray(data.alerts) ? data.alerts : [];
      console.log('Processed alerts count:', alerts.length);

      return alerts;
    } catch (error) {
      console.error('Error fetching user alerts:', error);
      // Return empty array instead of throwing to prevent dashboard failure
      return [];
    }
  },

  async getAreaCoordinates(area) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/areas/${area}/coordinates`);

      if (!response.ok) {
        throw new Error(`Failed to fetch area coordinates: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching area coordinates:', error);
      throw error;
    }
  },

  async updateProfile(profileData, token) {
    try {
      console.log('🔄 Updating user profile...', profileData);

      const response = await fetch(`${API_BASE_URL}/auth/update-profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(profileData),
      });

      console.log('📡 Update profile response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ Update profile failed:', response.status, errorData);
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      const data = await response.json();
      console.log('✅ Profile updated successfully:', data);
      return data;
    } catch (error) {
      console.error('❌ Error updating profile:', error);
      throw error;
    }
  },

  // Location tracking API methods
  async updateLocation(token, locationData) {
    try {
      console.log('📍 Updating location:', locationData);
      const response = await fetch(`${API_BASE_URL}/location/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(locationData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update location');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating location:', error);
      throw error;
    }
  },

  async getLocationHistory(token, days = 7) {
    try {
      console.log('📚 Getting location history for', days, 'days');
      const response = await fetch(`${API_BASE_URL}/location/history?days=${days}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to get location history');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting location history:', error);
      throw error;
    }
  },

  async getLocationPreferences(token) {
    try {
      console.log('⚙️ Getting location preferences');
      const response = await fetch(`${API_BASE_URL}/location/preferences`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to get location preferences');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting location preferences:', error);
      throw error;
    }
  },

  async updateLocationPreferences(token, preferences) {
    try {
      console.log('⚙️ Updating location preferences:', preferences);
      const response = await fetch(`${API_BASE_URL}/location/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(preferences),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update location preferences');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating location preferences:', error);
      throw error;
    }
  },

  async clearLocationHistory(token, daysToKeep = null) {
    try {
      console.log('🗑️ Clearing location history, keeping', daysToKeep, 'days');
      const url = daysToKeep !== null
        ? `${API_BASE_URL}/location/history?days_to_keep=${daysToKeep}`
        : `${API_BASE_URL}/location/history`;

      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to clear location history');
      }

      return await response.json();
    } catch (error) {
      console.error('Error clearing location history:', error);
      throw error;
    }
  },

  async reverseGeocode(token, lat, lng) {
    try {
      console.log('🗺️ Reverse geocoding coordinates:', lat, lng);
      const response = await fetch(`${API_BASE_URL}/location/reverse-geocode?lat=${lat}&lng=${lng}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to reverse geocode coordinates');
      }

      return await response.json();
    } catch (error) {
      console.error('Error reverse geocoding:', error);
      throw error;
    }
  },

  // NOTE: duplicate removed — getAreas() and getCrimeTypes() are defined earlier in this file
  // and return {name, coordinates} objects / string arrays respectively.

  // SuperAdmin Analytics API Methods
  async getCrimeTrends(token, params = {}) {
    try {
      console.log('📊 Fetching crime trends...');
      const queryString = buildQueryString(params);
      const response = await this.get(`/admin/analytics/crime-trends${queryString}`, token);

      // Transform backend data to expected format
      if (response && Array.isArray(response.trends)) {
        return response.trends.map(item => ({
          date: item.date || item.time_period,
          actual: item.actual || item.actual_count || item.count || 0,
          predicted: item.predicted || item.predicted_count || item.prediction || 0
        }));
      }

      return response;
    } catch (error) {
      console.error('Error fetching crime trends:', error);
      throw error;
    }
  },

  async getPredictiveAnalytics(token, params = {}) {
    try {
      console.log('🔮 Fetching predictive analytics...');
      const queryString = buildQueryString(params);
      const response = await this.get(`/admin/analytics/predictive${queryString}`, token);

      return {
        patterns: response.patterns || [],
        risk_heatmap: response.risk_heatmap || response.heatmap || []
      };
    } catch (error) {
      console.error('Error fetching predictive analytics:', error);
      throw error;
    }
  },

  async getAreaAnalysis(token, params = {}) {
    try {
      console.log('🗺️ Fetching area analysis...');
      const queryString = buildQueryString(params);
      const response = await this.get(`/admin/analytics/area-analysis${queryString}`, token);

      if (response && Array.isArray(response.areas)) {
        return {
          areas: response.areas.map(area => ({
            name: area.name || area.area,
            crime_count: parseInt(area.crime_count || area.count || 0),
            risk_level: area.risk_level || 'Unknown'
          }))
        };
      }

      return { areas: [] };
    } catch (error) {
      console.error('Error fetching area analysis:', error);
      throw error;
    }
  },

  async getAdminStats(token) {
    try {
      console.log('📈 Fetching admin stats...');
      const response = await this.get('/admin/stats', token);

      // Normalize response to expected format – keep ALL backend fields
      return {
        totalUsers: response.total_users || response.totalUsers || 0,
        total_users: response.total_users || response.totalUsers || 0,
        totalAdmins: response.total_admins || response.totalAdmins || 0,
        total_admins: response.total_admins || response.totalAdmins || 0,
        totalCrimes: response.total_crimes || response.totalCrimes || 0,
        total_crimes: response.total_crimes || response.totalCrimes || 0,
        recentCrimes: response.recent_crimes || response.recentCrimes || 0,
        recent_crimes: response.recent_crimes || response.recentCrimes || 0,
        crimesByRisk: response.crimes_by_risk || response.crimesByRisk || {},
        crimes_by_risk: response.crimes_by_risk || response.crimesByRisk || {},
        crimesByArea: response.crimes_by_area || response.crimesByArea || {},
        crimes_by_area: response.crimes_by_area || response.crimesByArea || {},
        activeReports: response.active_reports || response.activeReports || 0,
        active_reports: response.active_reports || response.activeReports || 0,
        systemHealth: response.system_health || response.systemHealth || 98,
        system_health: response.system_health || response.systemHealth || 98,
        predictionsToday: response.predictions_today || response.predictionsToday || 0,
        predictions_today: response.predictions_today || response.predictionsToday || 0,
        pending_approvals: response.pending_approvals || response.pendingApprovals || 0,
        pendingApprovals: response.pending_approvals || response.pendingApprovals || 0,
        preventedCrimes: response.prevented_crimes || response.preventedCrimes || 0
      };
    } catch (error) {
      console.error('Error fetching admin stats:', error);
      throw error;
    }
  },

  async getAdminRecentEvents(token) {
    try {
      const response = await this.get('/admin/recent-events', token);
      if (response && Array.isArray(response.events)) return response.events;
      if (Array.isArray(response)) return response;
      return [];
    } catch (error) {
      console.error('Error fetching admin recent events:', error);
      return [];
    }
  },

  async getAdminNotifications(token) {
    try {
      console.log('🔔 Fetching admin notifications...');
      const response = await this.get('/admin/notifications', token);

      // Return array of notifications
      if (Array.isArray(response)) {
        return response;
      } else if (response && Array.isArray(response.notifications)) {
        return response.notifications;
      }

      return [];
    } catch (error) {
      console.error('Error fetching admin notifications:', error);
      throw error;
    }
  },

  async getUniqueAreas(token) {
    try {
      console.log('📍 Fetching unique areas from crimes...');
      const response = await this.get('/api/crimes/areas', token);

      if (Array.isArray(response)) {
        return response;
      } else if (response && Array.isArray(response.areas)) {
        return response.areas;
      }

      // Fallback to general areas endpoint
      return await this.getAreas();
    } catch (error) {
      console.error('Error fetching unique areas:', error);
      // Fallback to general areas endpoint
      return await this.getAreas();
    }
  },

  // ==================== REPORTING METHODS ====================

  async getReportHistory(token, limit = 50, offset = 0) {
    try {
      console.log('📊 Fetching report history...');
      const response = await this.get(`/admin/reports/history?limit=${limit}&offset=${offset}`, token);

      return response.reports || [];
    } catch (error) {
      console.error('Error fetching report history:', error);
      return [];
    }
  },

  async getScheduledReports(token) {
    try {
      console.log('📅 Fetching scheduled reports...');
      const response = await this.get('/admin/reports/scheduled', token);

      return response.scheduled_reports || [];
    } catch (error) {
      console.error('Error fetching scheduled reports:', error);
      return [];
    }
  },

  async generateCustomReport(token, filters) {
    try {
      console.log('📝 Generating custom report...');
      const response = await this.post('/admin/reports/generate', {
        report_type: filters.report_type || filters.reportType,
        start_date: filters.start_date,
        end_date: filters.end_date,
        format: filters.format || 'pdf',
        title: filters.title || filters.report_name || null,
        filters: filters
      }, token);

      return response;
    } catch (error) {
      console.error('Error generating custom report:', error);
      throw error;
    }
  },

  async scheduleReport(token, scheduleData) {
    try {
      console.log('⏰ Scheduling report...');
      const response = await this.post('/admin/reports/schedule', {
        report_type: scheduleData.report_type || scheduleData.reportType,
        frequency: scheduleData.schedule,
        recipients: scheduleData.recipients || [],
        format: scheduleData.format || 'pdf'
      }, token);

      return response;
    } catch (error) {
      console.error('Error scheduling report:', error);
      throw error;
    }
  },

  async clearReportHistory(token) {
    try {
      console.log('🧹 Clearing report history...');
      const response = await fetch(`${API_BASE_URL}/admin/reports/history`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to clear report history');
      }
      return data;
    } catch (error) {
      console.error('Error clearing report history:', error);
      throw error;
    }
  },

  async downloadReport(token, reportId) {
    try {
      console.log(`📥 Downloading report ${reportId}...`);
      // This would typically trigger a file download
      const response = await this.get(`/admin/reports/download/${reportId}`, token);

      return response;
    } catch (error) {
      console.error('Error downloading report:', error);
      throw error;
    }
  },

  async getUserStats(token, lat = null, lng = null, area = null, timeFilter = null) {
    try {
      // If area is provided, fetch comprehensive area safety profile for dashboard cards.
      // Use dashboard-specific mapper to avoid clashing with the raw profile method used by profile panels.
      if (area) {
        return await this.getAreaSafetyProfileForDashboard(token, area, lat, lng, timeFilter);
      }

      // Otherwise, fetch basic user activity stats
      let url = `${API_BASE_URL}/api/auth/me/stats`;
      const params = [];
      if (lat !== null && lat !== undefined) params.push(`latitude=${lat}`);
      if (lng !== null && lng !== undefined) params.push(`longitude=${lng}`);
      if (timeFilter) params.push(`time_filter=${encodeURIComponent(timeFilter)}`);

      if (params.length > 0) {
        url += `?${params.join('&')}`;
      }

      console.log('Fetching user basic stats from:', url);
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new Error(`Failed to fetch user stats (${response.status}): ${errorText || response.statusText}`);
      }

      const data = await response.json();
      console.log('User stats response:', data);
      return data;
    } catch (error) {
      console.error('Error fetching user stats:', error);
      throw error;
    }
  },

  async getAreaSafetyProfileForDashboard(token, area, lat = null, lng = null, timeFilter = null) {
    try {
      const params = new URLSearchParams();
      params.append('area', area);

      // Use exact day windows when possible so selected filter matches backend scope.
      if (timeFilter === '7d') {
        params.append('days', '7');
      } else if (timeFilter === '30d') {
        params.append('days', '30');
      } else {
        let months = 12; // default
        if (timeFilter === '12m') months = 12;
        else if (timeFilter === 'all') months = 36; // max allowed
        params.append('months', months.toString());
      }

      if (lat !== null && lng !== null) {
        params.append('lat', lat.toString());
        params.append('lng', lng.toString());
        params.append('radius_km', '2.0'); // 2km radius for local area
      }

      const url = `${API_BASE_URL}/api/crimes/area-safety-profile?${params.toString()}`;
      console.log('Fetching area safety profile from:', url);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Area safety profile response:', data);

      // Map top crime types to expected format for risk factors
      const topCrimesList = (data.top_crime_types || []).map((crimeType, index) => {
        const label =
          crimeType.display_name ||
          crimeType.display_type ||
          crimeType.type ||
          crimeType.crime_type ||
          crimeType.name ||
          'Unknown';

        const count = Number(crimeType.count || crimeType.cnt || 0);
        const percentage =
          typeof crimeType.percentage === 'number'
            ? crimeType.percentage
            : typeof crimeType.pct === 'number'
              ? crimeType.pct
              : Math.round((count / Math.max(1, data.total_crimes || 0)) * 100);

        return {
          crime_type: label,
          display_name: label,
          count,
          percentage,
        };
      });

      // Generate trend data from monthly crime counts or create synthetic data
      let trendData = [];
      let trendLabels = [];

      if (data.monthly_crime_counts && Array.isArray(data.monthly_crime_counts)) {
        // Use actual monthly data if available
        // Use actual monthly/weekly/daily data if available from the new backend format
        trendData = data.monthly_crime_counts.slice(-15).map(item => item.count || 0);
        trendLabels = data.monthly_crime_counts.slice(-15).map(item => item.label || item.period || item.month || '');
      } else {
        // Generate synthetic trend data based on total crimes
        const totalCrimes = data.total_crimes || 0;
        const monthlyAvg = Math.max(1, Math.floor(totalCrimes / 12));

        // Create 12 months of data with some variation
        for (let i = 0; i < 12; i++) {
          const variation = Math.random() * 0.4 - 0.2; // ±20% variation
          trendData.push(Math.max(0, Math.floor(monthlyAvg * (1 + variation))));

          const date = new Date();
          date.setMonth(date.getMonth() - (11 - i));
          trendLabels.push(date.toLocaleDateString('en-US', { month: 'short' }));
        }
      }

      // Calculate breakdown by crime categories
      const breakdown = {
        violent: 0,
        property: 0,
        personal: 0,
        day: Math.floor((data.total_crimes || 0) * 0.6), // Estimated 60% day incidents
        night: Math.floor((data.total_crimes || 0) * 0.4) // Estimated 40% night incidents
      };

      // Map crime types to categories for breakdown
      (data.top_crime_types || []).forEach(crimeType => {
        const type = (crimeType.crime_type || '').toLowerCase();
        const count = crimeType.count || 0;

        if (type.includes('murder') || type.includes('assault') || type.includes('robbery') || type.includes('dacoity')) {
          breakdown.violent += count;
        } else if (type.includes('theft') || type.includes('burglary') || type.includes('vehicle') || type.includes('snatching')) {
          breakdown.property += count;
        } else {
          breakdown.personal += count;
        }
      });

      // Transform the response to match what the frontend expects
      return {
        safety_score: data.safety_score || 50,
        safety_score_change: data.trend?.change_pct || 0,
        weekly_alerts: Math.min(data.total_crimes || 0, 50), // Cap for display
        weekly_alerts_change: data.trend?.change_pct || 0,
        safe_routes: 0, // Not available in area profile
        nearest_safe_zone: 0, // Not available in area profile
        safe_zone_name: 'N/A',
        breakdown: breakdown,
        confidence: data.data_confidence || 'none',
        risk_level: data.risk_level || 'Unknown',
        total_crimes: data.total_crimes || 0,
        incidents_7d: data.last_7_days || 0,
        incidents_30d: data.last_30_days || 0,
        incidents_24h: data.last_24_h || 0,
        incidents_all: data.total_crimes || 0,
        high_risk_crimes: data.high_risk_count || 0,
        medium_risk_crimes: data.medium_risk_count || 0,

        // Align with keys expected by UserDashboard.jsx metric cards
        recent_7d_crimes: data.last_7_days || 0,
        recent_30d_crimes: data.last_30_days || 0,

        // Add the missing fields for risk factors and trends
        top_crimes_list: topCrimesList,
        trend_data: trendData,
        trend_labels: trendLabels,

        system_status: data.low_data_warning ? [
          { type: 'warning', message: data.low_data_warning, time: new Date().toISOString() }
        ] : [
          { type: 'info', message: 'Area analysis complete', time: new Date().toISOString() }
        ],
        resolved_area: data.area || area
      };
    } catch (error) {
      console.error('Error fetching area safety profile:', error);
      throw error;
    }
  },

  // ===== Approval Workflow Methods =====

  async submitApprovalRequest(token, actionType, targetType = 'user', targetId = null, requestData = {}) {
    try {
      const params = new URLSearchParams({ action_type: actionType, target_type: targetType });
      if (targetId) params.append('target_id', targetId);

      const response = await fetch(`${API_BASE_URL}/admin/approval-request?${params.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(requestData),
      });

      if (response.status === 401) {
        throw new Error('SESSION_EXPIRED');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit approval request');
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async getMyApprovalRequests(token, limit = 50) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/my-approval-requests?limit=${limit}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch approval requests');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching approval requests:', error);
      throw error;
    }
  },

  async getPendingApprovals(token, limit = 100) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/pending-approvals?limit=${limit}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch pending approvals');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
      throw error;
    }
  },

  async reviewApproval(token, requestId, approved, notes = null, editedData = null) {
    try {
      const params = new URLSearchParams({ approved: approved.toString() });
      if (notes) params.append('notes', notes);

      const response = await fetch(`${API_BASE_URL}/admin/review-approval/${requestId}?${params.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: editedData ? JSON.stringify(editedData) : undefined,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to review approval request');
      }
      return await response.json();
    } catch (error) {
      console.error('Error reviewing approval:', error);
      throw error;
    }
  },

  // Returns the full approval request including fir_image_base64 (superadmin only)
  async getApprovalRequest(token, requestId) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/approval-request/${requestId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch approval request');
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  },

  async exportFilteredReport(token, { format = 'pdf', start_date, end_date, area, crime_type } = {}) {
    try {
      const params = new URLSearchParams({ format });
      if (start_date) params.append('start_date', start_date);
      if (end_date) params.append('end_date', end_date);
      if (area && area !== 'all') params.append('area', area);
      if (crime_type && crime_type !== 'all') params.append('crime_type', crime_type);

      const response = await fetch(`${API_BASE_URL}/admin/reports/export-filtered?${params.toString()}`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to export report');
      }

      const blob = await response.blob();
      const ext = format === 'excel' ? 'xlsx' : 'pdf';
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `crime_report_${new Date().toISOString().split('T')[0]}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting filtered report:', error);
      throw error;
    }
  },

  // ==========================================
  // LAW SECTIONS MANAGEMENT (PPC/ATA/CNSA etc.)
  // ==========================================

  async getLawSections(token, params = {}) {
    const qs = buildQueryString(params);
    return this.get(`/api/law-sections${qs}`, token);
  },

  async getLawSectionStats(token) {
    return this.get('/api/law-sections/stats', token);
  },

  async getLawTypes(token) {
    return this.get('/api/law-sections/law-types', token);
  },

  async lookupLawSection(sectionNumber, lawType = 'PPC') {
    return this.get(`/api/law-sections/lookup/${encodeURIComponent(sectionNumber)}?law_type=${lawType}`);
  },

  async verifyLawSectionAI(token, sectionNumber, lawType = 'PPC') {
    const response = await fetch(`${API_BASE_URL}/api/law-sections/verify-ai?law_type=${encodeURIComponent(lawType)}&section_number=${encodeURIComponent(sectionNumber)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'AI verification failed');
    }
    return response.json();
  },

  async updateLawSection(token, sectionId, data) {
    return this.put(`/api/law-sections/${sectionId}`, data, token);
  },

  async approveAISuggestion(token, sectionId, aiTitle) {
    return this.post(`/api/law-sections/approve-ai/${sectionId}`, { ai_title: aiTitle }, token);
  },

  async seedLawSections(token) {
    return this.post('/api/law-sections/seed', {}, token);
  },

  async getLawSectionAudit(token, sectionId) {
    return this.get(`/api/law-sections/audit/${sectionId}`, token);
  },

  async scanMissingPPCs(token) {
    return this.post('/api/law-sections/ppc/scan-missing', {}, token);
  },

  async insertLawSection(token, data) {
    return this.post('/api/law-sections/insert', data, token);
  },

}


export { apiService, API_BASE_URL };
export default apiService;

