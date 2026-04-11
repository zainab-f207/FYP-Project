/**
 * Secure PostMessage Service for SafeVision
 * Handles cross-origin communication with proper origin validation
 */

class PostMessageService {
  constructor() {
    this.allowedOrigins = this.getAllowedOrigins();
    this.messageHandlers = new Map();
    this.isInitialized = false;
  }

  /**
   * Get allowed origins from environment or fallback to development URLs
   */
  getAllowedOrigins() {
    // In production, this would come from environment variables
    // For now, using the same origins as backend CORS
    const defaultOrigins = [
      'http://localhost:5173',
      'http://127.0.0.1:5173',
      'http://localhost:3000',
      'http://127.0.0.1:3000',
      'http://localhost:5174',
      'http://127.0.0.1:5174',
      'http://192.168.0.104:5173',
      'http://192.168.56.1:5173'
    ];

    // Check for environment variable (would be set by build process)
    const envOrigins = import.meta.env?.VITE_ALLOWED_ORIGINS;
    if (envOrigins) {
      return envOrigins.split(',').map(origin => origin.trim());
    }

    return defaultOrigins;
  }

  /**
   * Validate if origin is allowed
   */
  isOriginAllowed(origin) {
    if (!origin) return false;

    // Check exact matches
    if (this.allowedOrigins.includes(origin)) {
      return true;
    }

    // Check if origin matches any allowed pattern (for subdomains, etc.)
    try {
      const originUrl = new URL(origin);
      return this.allowedOrigins.some(allowed => {
        try {
          const allowedUrl = new URL(allowed);
          // Allow if same protocol, host, and port
          return originUrl.protocol === allowedUrl.protocol &&
                 originUrl.host === allowedUrl.host;
        } catch {
          return false;
        }
      });
    } catch {
      return false;
    }
  }

  /**
   * Initialize the postMessage listener
   */
  initialize() {
    if (this.isInitialized) return;

    window.addEventListener('message', this.handleMessage.bind(this), false);
    this.isInitialized = true;

    console.log('🔒 PostMessage service initialized with allowed origins:', this.allowedOrigins);
  }

  /**
   * Handle incoming postMessage events
   */
  handleMessage(event) {
    try {
      // Validate origin
      if (!this.isOriginAllowed(event.origin)) {
        console.warn('🚫 Blocked message from unauthorized origin:', event.origin);
        return;
      }

      const { type, data, requestId } = event.data || {};

      if (!type) {
        console.warn('⚠️ Received message without type:', event.data);
        return;
      }

      console.log('📨 Received secure message:', { type, origin: event.origin, requestId });

      // Handle built-in message types
      switch (type) {
        case 'PING':
          this.sendMessage(event.source, { type: 'PONG', requestId }, event.origin);
          break;

        case 'HEALTH_CHECK':
          this.sendMessage(event.source, {
            type: 'HEALTH_RESPONSE',
            data: { status: 'healthy', timestamp: Date.now() },
            requestId
          }, event.origin);
          break;

        default:
          // Check for custom handlers
          const handler = this.messageHandlers.get(type);
          if (handler) {
            handler(event.data, event.source, event.origin, requestId);
          } else {
            console.warn('⚠️ No handler for message type:', type);
          }
      }
    } catch (error) {
      console.error('❌ Error handling postMessage:', error);
    }
  }

  /**
   * Register a custom message handler
   */
  on(type, handler) {
    if (typeof handler !== 'function') {
      throw new Error('Handler must be a function');
    }
    this.messageHandlers.set(type, handler);
    console.log('📝 Registered message handler for:', type);
  }

  /**
   * Remove a message handler
   */
  off(type) {
    this.messageHandlers.delete(type);
    console.log('🗑️ Removed message handler for:', type);
  }

  /**
   * Send a message to a target window
   */
  sendMessage(targetWindow, message, targetOrigin = '*') {
    if (!targetWindow || typeof targetWindow.postMessage !== 'function') {
      throw new Error('Invalid target window');
    }

    // Add timestamp for debugging
    const messageWithMeta = {
      ...message,
      timestamp: Date.now(),
      source: 'SafeVision'
    };

    console.log('📤 Sending message:', messageWithMeta, 'to origin:', targetOrigin);
    targetWindow.postMessage(messageWithMeta, targetOrigin);
  }

  /**
   * Send a message with response handling
   */
  sendRequest(targetWindow, type, data, targetOrigin = '*', timeout = 5000) {
    return new Promise((resolve, reject) => {
      const requestId = this.generateRequestId();

      // Set up response handler
      const responseHandler = (responseData, source, origin, responseRequestId) => {
        if (responseRequestId === requestId) {
          clearTimeout(timeoutId);
          this.off(`${type}_RESPONSE_${requestId}`);
          resolve({ data: responseData, source, origin });
        }
      };

      // Register temporary handler for response
      this.on(`${type}_RESPONSE_${requestId}`, responseHandler);

      // Set timeout
      const timeoutId = setTimeout(() => {
        this.off(`${type}_RESPONSE_${requestId}`);
        reject(new Error(`Request timeout: ${type}`));
      }, timeout);

      // Send the request
      this.sendMessage(targetWindow, {
        type,
        data,
        requestId
      }, targetOrigin);
    });
  }

  /**
   * Generate unique request ID
   */
  generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Open a popup window and establish secure communication
   */
  openSecurePopup(url, windowFeatures = 'width=500,height=600') {
    const popup = window.open(url, '_blank', windowFeatures);

    if (!popup) {
      throw new Error('Popup blocked by browser');
    }

    return new Promise((resolve, reject) => {
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          reject(new Error('Popup was closed'));
        }
      }, 1000);

      // Wait for popup to load and respond to ping
      const timeout = setTimeout(() => {
        clearInterval(checkClosed);
        reject(new Error('Popup communication timeout'));
      }, 10000);

      // Send initial ping to establish connection
      const establishConnection = async () => {
        try {
          const response = await this.sendRequest(popup, 'PING', null, '*', 2000);
          clearTimeout(timeout);
          clearInterval(checkClosed);
          resolve(popup);
        } catch (error) {
          // Retry connection establishment
          setTimeout(establishConnection, 500);
        }
      };

      // Start connection establishment after popup has time to load
      setTimeout(establishConnection, 1000);
    });
  }

  /**
   * Clean up resources
   */
  destroy() {
    if (this.isInitialized) {
      window.removeEventListener('message', this.handleMessage.bind(this));
      this.messageHandlers.clear();
      this.isInitialized = false;
      console.log('🧹 PostMessage service destroyed');
    }
  }
}

// Create singleton instance
const postMessageService = new PostMessageService();

export default postMessageService;
