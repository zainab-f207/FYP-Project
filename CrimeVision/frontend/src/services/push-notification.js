// push-notification.jsx
export class PushNotificationService {
  constructor() {
    this.registration = null;
    this.subscription = null;
    // Will be filled from server on initialize if not provided
    this.vapidPublicKey = null;
  }

  async initialize(vapidPublicKey = null) {
    try {
      console.log('🔄 Initializing push notification service...');
      
      if (vapidPublicKey) {
        this.vapidPublicKey = vapidPublicKey;
      } else if (!this.vapidPublicKey) {
        // Attempt to fetch VAPID public key from server
        try {
          const resp = await fetch(`${API_BASE_URL}/api/alerts/vapid-public-key`);
          if (resp.ok) {
            const data = await resp.json();
            if (data && data.publicKey) {
              this.vapidPublicKey = data.publicKey;
              console.log('✅ Fetched VAPID public key from server');
            }
          } else {
            console.warn('⚠️ Could not fetch VAPID public key from server:', resp.status);
          }
        } catch (err) {
          console.warn('⚠️ Error fetching VAPID public key:', err);
        }
      }

      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.warn('❌ Push notifications are not supported in this browser');
        return false;
      }

      // Register service worker if not already registered
      if (!this.registration) {
        this.registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'none'
        });
        console.log('✅ Service Worker registered:', this.registration);
      }

      // Wait for service worker to be ready
      await navigator.serviceWorker.ready;
      console.log('✅ Service Worker ready');

      // Check if already subscribed
      this.subscription = await this.registration.pushManager.getSubscription();
      if (this.subscription) {
        console.log('📱 Existing push subscription found');
      }

      return true;
    } catch (error) {
      console.error('❌ Service Worker registration failed:', error);
      return false;
    }
  }

  async subscribe() {
    try {
      console.log('🔔 Creating push subscription...');

      if (!this.registration) {
        const initialized = await this.initialize();
        if (!initialized) {
          throw new Error('Push notification service initialization failed');
        }
      }

      // If already subscribed, return the existing subscription data
      if (this.subscription) {
        return this.getSubscriptionData(this.subscription);
      }

      // Request notification permission if not already granted
      if (Notification.permission !== 'granted') {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          throw new Error('Notification permission denied');
        }
      }

      // Subscribe to push notifications
      if (!this.vapidPublicKey) {
        throw new Error('VAPID public key not available for push subscription');
      }

      this.subscription = await this.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
      });

      console.log('✅ Push subscription created');
      return this.getSubscriptionData(this.subscription);
    } catch (error) {
      console.error('❌ Failed to subscribe to push notifications:', error);
      throw new Error(`Push subscription failed: ${error.message}`);
    }
  }

  async unsubscribe() {
    try {
      if (!this.subscription) {
        console.log('ℹ️ No active push subscription found');
        return true;
      }

      await this.subscription.unsubscribe();
      this.subscription = null;
      console.log('✅ Successfully unsubscribed from push notifications');
      return true;
    } catch (error) {
      console.error('❌ Failed to unsubscribe from push notifications:', error);
      // Refresh local subscription reference from the browser
      try {
        this.subscription = await this.registration.pushManager.getSubscription();
      } catch (err) {
        console.warn('⚠️ Failed to get existing subscription:', err);
      }

      // If already subscribed, return the existing subscription data
      if (this.subscription) {
        console.log('📱 Existing push subscription found - reusing it');
        return this.getSubscriptionData(this.subscription);
      }

      throw error;
    }
  }

  getSubscriptionData(subscription) {
    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')),
        auth: this.arrayBufferToBase64(subscription.getKey('auth'))
      }
    };
  }

  // Helper method to convert URL-safe base64 to Uint8Array
  
    // Helper method to convert URL-safe base64 to Uint8Array
    urlBase64ToUint8Array(base64String) {
      const padding = '='.repeat((4 - base64String.length % 4) % 4);
      const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
      
      const rawData = window.atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      
      for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
      }
      return outputArray;
    }

  // Helper method to convert array buffer to base64
  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }

  // Method to test notifications
  async testNotification() {
    if (Notification.permission !== 'granted') {
      throw new Error('Notification permission not granted');
    }

    const notification = new Notification('SafeVision Test', {
      body: 'Browser notifications are working! You will receive safety alerts even when the app is closed.',
      icon: '/icon-192x192.png',
      badge: '/badge-72x72.png',
      tag: 'test-notification',
      requireInteraction: true,
      actions: [
        {
          action: 'view',
          title: 'Open App'
        }
      ]
    });

    return true;
  }
}

export default new PushNotificationService();
