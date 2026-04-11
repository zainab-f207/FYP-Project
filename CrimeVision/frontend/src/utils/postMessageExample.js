/**
 * Example usage of the PostMessageService for SafeVision
 * This file demonstrates how to use the secure postMessage functionality
 */

import postMessageService from '../services/postMessageService';

/**
 * Example: Request user authentication status from parent window
 */
export const requestAuthStatus = async () => {
  try {
    const response = await postMessageService.sendRequest(
      window.parent,
      'USER_AUTH_STATUS',
      { requestDetails: 'Check if user is logged in' },
      '*',
      5000
    );

    console.log('Auth status response:', response.data);
    return response.data.isAuthenticated;
  } catch (error) {
    console.error('Failed to get auth status:', error);
    return false;
  }
};

/**
 * Example: Request crime data from parent window
 */
export const requestCrimeData = async (area, filters = {}) => {
  try {
    const response = await postMessageService.sendRequest(
      window.parent,
      'CRIME_DATA_REQUEST',
      {
        area,
        filters,
        requestType: 'area_safety_score'
      },
      '*',
      10000
    );

    console.log('Crime data response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Failed to get crime data:', error);
    return null;
  }
};

/**
 * Example: Send user action to parent window (e.g., navigation, form submission)
 */
export const notifyUserAction = (actionType, actionData) => {
  postMessageService.sendMessage(
    window.parent,
    {
      type: 'USER_ACTION',
      data: {
        actionType, // 'navigation', 'form_submit', 'button_click', etc.
        actionData,
        timestamp: Date.now(),
        userAgent: navigator.userAgent
      }
    },
    '*'
  );
};

/**
 * Example: Open a secure popup for external authentication
 */
export const openAuthPopup = async (authUrl) => {
  try {
    const popup = await postMessageService.openSecurePopup(
      authUrl,
      'width=500,height=600,scrollbars=yes,resizable=yes'
    );

    // Set up listeners for auth completion
    postMessageService.on('AUTH_SUCCESS', (data, source, origin) => {
      if (source === popup) {
        console.log('Authentication successful:', data);
        popup.close();
        // Handle successful auth
        handleAuthSuccess(data);
      }
    });

    postMessageService.on('AUTH_ERROR', (data, source, origin) => {
      if (source === popup) {
        console.error('Authentication failed:', data);
        popup.close();
        // Handle auth error
        handleAuthError(data);
      }
    });

    return popup;
  } catch (error) {
    console.error('Failed to open auth popup:', error);
    throw error;
  }
};

/**
 * Example: Register custom message handlers for embedded components
 */
export const registerEmbeddedHandlers = () => {
  // Handle requests from parent for component state
  postMessageService.on('GET_COMPONENT_STATE', (data, source, origin, requestId) => {
    const componentState = {
      isVisible: true,
      currentView: 'map',
      userPreferences: {
        theme: 'light',
        language: 'en'
      }
    };

    postMessageService.sendMessage(source, {
      type: 'COMPONENT_STATE_RESPONSE',
      data: componentState,
      requestId
    }, origin);
  });

  // Handle theme change requests from parent
  postMessageService.on('CHANGE_THEME', (data, source, origin) => {
    const { theme } = data;
    console.log('Changing theme to:', theme);
    // Apply theme change logic here
    applyTheme(theme);

    // Confirm theme change
    postMessageService.sendMessage(source, {
      type: 'THEME_CHANGED',
      data: { newTheme: theme, success: true }
    }, origin);
  });

  // Handle resize requests
  postMessageService.on('RESIZE_COMPONENT', (data, source, origin) => {
    const { width, height } = data;
    console.log('Resizing component:', { width, height });
    // Apply resize logic here
    resizeComponent(width, height);
  });
};

/**
 * Example: Secure data sharing between windows
 */
export const shareDataSecurely = (targetWindow, data, allowedOrigins = []) => {
  // Only share with explicitly allowed origins
  const targetOrigin = allowedOrigins.includes(window.location.origin)
    ? window.location.origin
    : '*'; // Fallback, but not recommended

  postMessageService.sendMessage(targetWindow, {
    type: 'SECURE_DATA_SHARE',
    data: {
      payload: data,
      checksum: generateChecksum(data), // Add integrity check
      timestamp: Date.now()
    }
  }, targetOrigin);
};

/**
 * Helper: Generate simple checksum for data integrity
 */
const generateChecksum = (data) => {
  const str = JSON.stringify(data);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash.toString(36);
};

/**
 * Helper functions (implement based on your app's needs)
 */
const handleAuthSuccess = (data) => {
  // Handle successful authentication
  console.log('Auth success:', data);
  // Update app state, redirect user, etc.
};

const handleAuthError = (data) => {
  // Handle authentication error
  console.error('Auth error:', data);
  // Show error message, retry logic, etc.
};

const applyTheme = (theme) => {
  // Apply theme to component
  document.documentElement.setAttribute('data-theme', theme);
};

const resizeComponent = (width, height) => {
  // Resize component container
  const container = document.getElementById('component-container');
  if (container) {
    container.style.width = width + 'px';
    container.style.height = height + 'px';
  }
};

// Export for use in components
export default {
  requestAuthStatus,
  requestCrimeData,
  notifyUserAction,
  openAuthPopup,
  registerEmbeddedHandlers,
  shareDataSecurely
};
