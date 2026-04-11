// public/sw.js
self.addEventListener('install', (event) => {
  console.log('Service Worker installing.');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating.');
  return self.clients.claim();
});

self.addEventListener('push', (event) => {
  console.log('Push event received:', event);
  
  if (!event.data) {
    console.log('Push event but no data');
    return;
  }
  
  try {
    const data = event.data.json();
    console.log('Push data:', data);

    // Use the pre-built title/body from backend, or construct from structured data
    const title = data.title || 'SafeVision Safety Alert';
    const body  = data.body  || data.message || 'New safety update from SafeVision';

    // Pick icon & badge based on alert severity / type
    const alertType = (data.data && data.data.alert_type) || data.tag || '';
    const severity  = (data.data && data.data.severity)   || '';

    let icon  = '/info-icon.png';
    let badge = '/badge-72x72.png';
    let image = undefined;

    if (['critical_risk_zone', 'high_risk_zone', 'live_high_risk_zone', 'immediate_risk'].includes(alertType) ||
        ['critical', 'high'].includes(severity)) {
      icon  = '/warning-icon.png';
      image = '/warning-banner.png';
    } else if (alertType === 'medium_risk_zone' || severity === 'medium') {
      icon  = '/warning-icon.png';
    } else if (alertType === 'safe_area' || severity === 'low') {
      icon  = '/safe-icon.png';
    }

    // Determine action instructions based on severity
    let actionTitle = '📍 View Details';
    let actionDesc = 'See full analysis and map';
    
    if (severity === 'critical') {
      actionTitle = '🚨 See Critical Alert';
      actionDesc = 'Review critical information';
    } else if (severity === 'high') {
      actionTitle = '⚠️ View High Risk Details';
      actionDesc = 'See incident details and recommendations';
    } else if (severity === 'medium') {
      actionTitle = '📍 View Area Details';
      actionDesc = 'See analysis and stay informed';
    } else if (severity === 'low') {
      actionTitle = '✅ View Details';
      actionDesc = 'Safety confirmed';
    }

    const options = {
      body,
      icon,
      badge,
      image,
      vibrate: severity === 'critical' ? [200, 100, 200, 100, 200, 100, 200] : [100, 50, 100],
      data: data.data || data,
      tag: data.tag || 'safevision-alert',
      requireInteraction: ['critical', 'high'].includes(severity),
      renotify: true,
      silent: false,
      actions: [
        {
          action: 'view',
          title: actionTitle,
          icon: '/eye-icon.png'
        },
        {
          action: 'dismiss',
          title: '✕ Dismiss',
          icon: '/close-icon.png'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (error) {
    console.error('Error handling push event:', error);
    
    // Fallback notification
    event.waitUntil(
      self.registration.showNotification('SafeVision Alert', {
        body: 'New safety update from SafeVision',
        icon: '/icon-192x192.png',
        tag: 'safevision-fallback'
      })
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked, action:', event.action);
  event.notification.close();

  const data     = event.notification.data || {};
  const mapUrl   = data.map_url   || data.url || '/dashboard?tab=map';
  const routeUrl = data.route_url || '/dashboard?tab=routes';

  // Helper: open a URL, re-using an existing window tab if possible
  const openUrl = (url) => clients.matchAll({ type: 'window', includeUncontrolled: true })
    .then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          return client.navigate(url).then(() => client.focus());
        }
      }
      return clients.openWindow(url);
    });

  if (event.action === 'view_map') {
    // 🗺️ Open dashboard map tab with area pre-selected
    event.waitUntil(openUrl(mapUrl));
  } else if (event.action === 'safer_route') {
    // 🧭 Open dashboard routes tab with destination/avoid area pre-set
    event.waitUntil(openUrl(routeUrl));
  } else if (event.action === 'dismiss') {
    // Silently dismissed
    console.log('Notification dismissed');
  } else {
    // Default body click -> open map view
    event.waitUntil(openUrl(mapUrl));
  }
});

self.addEventListener('notificationclose', (event) => {
  console.log('Notification closed:', event);
});

// Handle background sync for offline functionality
self.addEventListener('sync', (event) => {
  console.log('Background sync:', event);
  if (event.tag === 'crimevision-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  console.log('Performing background sync...');
  // You can implement background data sync here
}