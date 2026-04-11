//           `🚒 Fire Department\n` +
//           `💊 Pharmacy\n\n` +
//           `Enter the service number (1-4) or name:`;

//         const choice = prompt(`🛡️ Emergency Services Directions\n\n${serviceOptions}`);

//         if (choice) {
//           const services = {
//             '1': 'police', 'police': 'police',
//             '2': 'hospital', 'hospital': 'hospital',
//             '3': 'fire', 'fire': 'fire',
//             '4': 'pharmacy', 'pharmacy': 'pharmacy'
//           };

//           const serviceType = services[choice.toLowerCase()];
//           if (serviceType) {
//             getEmergencyDirections(serviceType);
//           } else {
//             alert('❌ Please select a valid service (1-4)');
//           }
//         }
//       }
//     },
//     {
//       id: 'route-safety',
//       icon: 'fas fa-route',
//       label: 'Route Safety',
//       description: 'Plan safe routes and check area safety',
//       color: '#7c3aed',
//       gradient: 'linear-gradient(135deg, #7c3aed, #6d28d9)',
//       type: 'navigation',
//       action: () => {
//         const destination = prompt('🗺️ Route Safety Check\n\nEnter your destination address:');
//         if (destination) {
//           // Open navigation with safety overlay
//           const mapUrl = `https://www.google.com/maps/dir/?api=1&origin=${location?.lat},${location?.lng}&destination=${encodeURIComponent(destination)}&travelmode=driving`;
//           window.open(mapUrl, '_blank');

//           alert(`📍 Route Planning Started\n\nFrom: ${address || 'Your location'}\nTo: ${destination}\n\n✅ Safe route suggestions will be shown on map`);
//         }
//       }
//     }
//   ];

//   const handleActionClick = (action) => {
//     if (isLoading) return;

//     setActiveAction(action.id);

//     // Add haptic feedback if available
//     if (navigator.vibrate) {
//       navigator.vibrate(50);
//     }

//     // Execute the action
//     action.action();

//     // Reset active state after animation
//     setTimeout(() => setActiveAction(null), 600);
//   };

//   const getActionBadge = (type) => {
//     const badges = {
//       safety: { text: 'LIVE', color: '#10b981' },
//       alert: { text: 'ALERTS', color: '#f59e0b' },
//       resource: { text: 'EMERGENCY', color: '#dc2626' },
//       navigation: { text: 'ROUTES', color: '#7c3aed' }
//     };

//     return badges[type] || { text: 'ACTION', color: '#6b7280' };
//   };

//   const showBrowserPushPrompt = browserPushSupported && !user?.browser_notifications_enabled;

//   return (
//     <section className={`${styles.quickActionsSection} ${isVisible ? styles.visible : ''}`}>
//       <div className={styles.container}>
//         {/* Browser Push Setup Prompt */}
//         {showBrowserPushPrompt && (
//           <div className={styles.browserPushPrompt}>
//             <div className={styles.browserPushPromptContent}>
//               <i className="fas fa-bell"></i>
//               <div className={styles.browserPushPromptText}>
//                 <h4>Enable Browser Notifications</h4>
//                 <p>Get instant safety alerts directly in your browser</p>
//               </div>
//               <button
//                 onClick={() => setShowBrowserPushSettings(true)}
//                 className={styles.setupButton}
//               >
//                 Enable Notifications
//               </button>
//             </div>
//           </div>
//         )}

//         {/* Location Tracking Toggle */}
//         {token && (
//           <div className={styles.locationTrackingSection}>
//             <LocationTrackingToggle
//               isEnabled={locationTrackingEnabled}
//               onToggle={handleLocationTrackingToggle}
//               permission={locationPermission}
//               status={locationTrackingStatus}
//               loading={locationTrackingLoading}
//             />
//           </div>
//         )}

//         {/* Header */}
//         <div className={styles.header}>
//           <div className={styles.badge}>
//             <i className="fas fa-bolt"></i>
//             <span>Safety Tools</span>
//           </div>
//           <h2 className={styles.title}>Enhanced Safety Features</h2>
//           <p className={styles.subtitle}>
//             Real-time safety assessment and emergency resources
//           </p>
//         </div>

//         {/* Actions Grid */}
//         <div className={styles.grid}>
//           {actions.map((action, index) => {
//             const badge = getActionBadge(action.type);

//             return (
//               <div
//                 key={action.id}
//                 className={`${styles.card} ${activeAction === action.id ? styles.active : ''} ${isLoading ? styles.loading : ''}`}
//                 style={{
//                   '--action-color': action.color,
//                   '--action-gradient': action.gradient,
//                   animationDelay: `${index * 100}ms`
//                 }}
//                 onClick={() => handleActionClick(action)}
//               >
//                 {/* Loading Overlay */}
//                 {isLoading && activeAction === action.id && (
//                   <div className={styles.loadingOverlay}>
//                     <div className={styles.loadingSpinner}>
//                       <i className="fas fa-spinner fa-spin"></i>
//                     </div>
//                   </div>
//                 )}

//                 {/* Background Effects */}
//                 <div className={styles.background}>
//                   <div className={styles.orb}></div>
//                   <div className={styles.glow}></div>
//                 </div>

//                 {/* Badge */}
//                 <div
//                   className={styles.actionBadge}
//                   style={{ backgroundColor: badge.color }}
//                 >
//                   {badge.text}
//                 </div>

//                 {/* Icon */}
//                 <div className={styles.iconContainer}>
//                   <div
//                     className={styles.iconWrapper}
//                     style={{ background: action.gradient }}
//                   >
//                     <i className={action.icon}></i>
//                   </div>
//                 </div>

//                 {/* Content */}
//                 <div className={styles.content}>
//                   <h3 className={styles.label}>{action.label}</h3>
//                   <p className={styles.description}>{action.description}</p>

//                   {action.id === 'safety-check' && safetyScore && (
//                     <div className={styles.safetyInfo}>
//                       <span className={styles.safetyScore}>
//                         {safetyScore.score}% Safe
//                       </span>
//                       <span className={styles.safetyLevel}>
//                         {safetyScore.level}
//                       </span>
//                       {safetyScore.source === 'backend' && (
//                         <span className={styles.safetySource}>
//                           Official Data
//                         </span>
//                       )}
//                     </div>
//                   )}

//                   {action.id === 'live-alerts' && userAlerts.length > 0 && (
//                     <div className={styles.alertInfo}>
//                       <span className={styles.alertCount}>
//                         {userAlerts.length} Active
//                       </span>
//                     </div>
//                   )}
//                 </div>

//                 {/* Arrow */}
//                 <div className={styles.arrow}>
//                   <i className="fas fa-chevron-right"></i>
//                 </div>
//               </div>
//             );
//           })}
//         </div>

//         {/* Status Footer */}
//         <div className={styles.footer}>
//           <div className={styles.statusGrid}>
//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className="fas fa-shield-check"></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Safety Status</span>
//                 <span className={styles.statusValue}>
//                   {safetyScore ? `${safetyScore.score}% - ${safetyScore.level}` : 'Checking...'}
//                 </span>
//               </div>
//             </div>

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className={`fas ${location ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Location</span>
//                 <span className={styles.statusValue}>
//                   {location ? 'Active' : 'Required'}
//                 </span>
//               </div>
//             </div>

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className="fas fa-bell"></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Alerts</span>
//                 <span className={styles.statusValue}>
//                   {userAlerts.length} Active
//                 </span>
//               </div>
//             </div>

//             {/* Browser Push Status */}
//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className={`fas ${user?.browser_notifications_enabled ? 'fa-bell' : 'fa-bell-slash'}`}></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Browser Alerts</span>
//                 <span className={styles.statusValue}>
//                   {user?.browser_notifications_enabled ? 'Enabled' : browserPushSupported ? 'Available' : 'Unsupported'}
//                 </span>
//               </div>
//             </div>

//             {/* Location Tracking Status */}
//             {token && (
//               <div className={styles.statusItem}>
//                 <div className={styles.statusIcon}>
//                   <i className={`fas ${locationTrackingEnabled ? 'fa-location-arrow' : 'fa-location-crosshairs'}`}></i>
//                 </div>
//                 <div className={styles.statusContent}>
//                   <span className={styles.statusLabel}>Location Tracking</span>
//                   <span className={styles.statusValue}>
//                     {locationTrackingEnabled ? 'Active' : 'Inactive'}
//                   </span>
//                 </div>
//               </div>
//             )}
//           </div>

//           {/* Location Info */}
//           {address && (
//             <div className={styles.locationInfo}>
//               <i className="fas fa-map-marker-alt"></i>
//               <span>{address}</span>
//             </div>
//           )}
//         </div>
//       </div>

//       {showBrowserPushSettings && (
//         <div className={styles.modalOverlay}>
//           <div className={styles.modalContent}>
//             <BrowserPushSettings
//               user={user}
//               token={token}
//               onUpdate={() => {
//                 // Refresh user data
//                 window.location.reload();
//               }}
//               onClose={() => setShowBrowserPushSettings(false)}
//             />
//           </div>
//         </div>
//       )}
//     </section>
//   );
// };

// export default QuickActions;



// src/components/UserDashboard/QuickActions.jsx
// import React, { useState, useEffect } from 'react';
// import { useAuth } from '../../contexts/AuthContext_updated';
// import apiService from '../../services/apiService_updated';
// import BrowserPushSettings from '../UserDashboard/BrowserNotifications';
// import styles from '../UserDashboard/QuickActions.module.css';

// // Enhanced Location Tracking Toggle Component
// const LocationTrackingToggle = ({ isEnabled, onToggle, permission, status, loading, deviceType }) => {
//   const getStatusColor = () => {
//     if (status.error) return '#dc2626';
//     if (status.isTracking) return '#10b981';
//     if (permission === 'denied') return '#f59e0b';
//     if (permission === 'prompt') return '#f59e0b';
//     return '#6b7280';
//   };

//   const getStatusText = () => {
//     if (loading) return 'Updating...';
//     if (status.error) return 'Error';
//     if (status.isTracking) {
//       const accuracy = status.lastPosition?.accuracy;
//       if (accuracy) {
//         return `Active (${Math.round(accuracy)}m)`;
//       }
//       return 'Active';
//     }
//     if (permission === 'denied') return 'Permission Required';
//     if (permission === 'prompt') return 'Click to Enable';
//     return 'Inactive';
//   };

//   const getStatusDescription = () => {
//     if (permission === 'denied') {
//       return deviceType === 'mobile' 
//         ? 'Enable location in browser and device settings'
//         : 'Allow location access in browser settings';
//     }
    
//     if (status.lastPosition?.accuracy) {
//       const accuracy = status.lastPosition.accuracy;
//       if (accuracy <= 100) return 'High accuracy GPS';
//       if (accuracy <= 500) return 'Good accuracy';
//       return 'Approximate location';
//     }
    
//     return deviceType === 'mobile' ? 'GPS tracking' : 'WiFi positioning';
//   };

//   return (
//     <div className={styles.locationToggle}>
//       <div className={styles.toggleHeader}>
//         <span className={styles.toggleLabel}>
//           Location Tracking 
//           <span className={styles.deviceType}>({deviceType})</span>
//         </span>
//         <div
//           className={styles.statusIndicator}
//           style={{ backgroundColor: getStatusColor() }}
//         >
//           {getStatusText()}
//         </div>
//       </div>

//       <div className={styles.toggleControls}>
//         <button
//           onClick={onToggle}
//           disabled={loading}
//           className={`${styles.toggleButton} ${isEnabled ? styles.active : ''} ${permission === 'denied' ? styles.disabled : ''}`}
//         >
//           <span className={styles.toggleSwitch}>
//             <span className={styles.toggleKnob}></span>
//           </span>
//           <span className={styles.toggleText}>
//             {isEnabled ? 'Enabled' : 'Disabled'}
//           </span>
//         </button>

//         <div className={styles.statusDescription}>
//           {getStatusDescription()}
//         </div>

//         {permission === 'denied' && (
//           <div className={styles.permissionGuidance}>
//             <i className="fas fa-info-circle"></i>
//             <span>
//               {deviceType === 'mobile' 
//                 ? 'Enable location in browser settings and device settings, then refresh'
//                 : 'Allow location access in browser settings'
//               }
//             </span>
//           </div>
//         )}

//         {status.lastUpdate && (
//           <div className={styles.lastUpdate}>
//             <i className="fas fa-clock"></i>
//             Last update: {new Date(status.lastUpdate).toLocaleTimeString()}
//           </div>
//         )}

//         {status.lastPosition?.accuracy && (
//           <div className={styles.accuracyInfo}>
//             <i className="fas fa-bullseye"></i>
//             Accuracy: {Math.round(status.lastPosition.accuracy)} meters
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// const QuickActions = () => {
//   const {
//     user,
//     token,
//     validateToken,
//     logout,
//     locationTrackingEnabled,
//     locationPermission,
//     currentLocation,
//     locationTrackingStatus,
//     startLocationTracking,
//     stopLocationTracking,
//     requestLocationPermission
//   } = useAuth();

//   const [activeAction, setActiveAction] = useState(null);
//   const [isVisible, setIsVisible] = useState(false);
//   const [location, setLocation] = useState(null);
//   const [address, setAddress] = useState('');
//   const [safetyScore, setSafetyScore] = useState(null);
//   const [isLoading, setIsLoading] = useState(false);
//   const [userAlerts, setUserAlerts] = useState([]);
//   const [showBrowserPushSettings, setShowBrowserPushSettings] = useState(false);
//   const [browserPushSupported, setBrowserPushSupported] = useState(false);
//   const [locationTrackingLoading, setLocationTrackingLoading] = useState(false);
//   const [deviceType, setDeviceType] = useState('desktop');

//   // Detect device type and capabilities
//   useEffect(() => {
//     const detectDeviceType = () => {
//       const userAgent = navigator.userAgent || navigator.vendor || window.opera;
//       const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
//       const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
//       const isSmallScreen = window.innerWidth <= 768;

//       setDeviceType(isMobile || (hasTouch && isSmallScreen) ? 'mobile' : 'desktop');
//     };

//     detectDeviceType();

//     // Check browser push support
//     if ('serviceWorker' in navigator && 'PushManager' in window) {
//       setBrowserPushSupported(true);
//     }
//   }, []);

//   // Enhanced location detection with permission state checking
//   useEffect(() => {
//     const getEnhancedLocation = async () => {
//       if (!navigator.geolocation) {
//         setAddress('Geolocation not supported');
//         return;
//       }

//       // Check permission state first
//       let permissionState = 'unknown';
//       try {
//         if (navigator.permissions) {
//           const permission = await navigator.permissions.query({ name: 'geolocation' });
//           permissionState = permission.state;

//           // Listen for permission changes
//           permission.onchange = () => {
//             console.log('📍 Permission state changed to:', permission.state);
//             // Update permission in AuthContext if needed
//           };
//         }
//       } catch (error) {
//         console.warn('📍 Permission query not supported:', error);
//       }

//       console.log('📍 Permission state:', permissionState);

//       // Fast WiFi positioning first (like inDrive)
//       const getFastLocation = () => {
//         return new Promise((resolve, reject) => {
//           navigator.geolocation.getCurrentPosition(resolve, reject, {
//             enableHighAccuracy: false, // Fast WiFi positioning first
//             timeout: 3000, // 3 seconds for instant response
//             maximumAge: 60000 // Accept 1 minute old location
//           });
//         });
//       };

//       // GPS for accuracy improvement (background)
//       const getGPSLocation = () => {
//         return new Promise((resolve, reject) => {
//           navigator.geolocation.getCurrentPosition(resolve, reject, {
//             enableHighAccuracy: true, // GPS precision
//             timeout: 8000, // 8 seconds for GPS
//             maximumAge: 30000 // Accept 30 seconds old location
//           });
//         });
//       };

//       try {
//         console.log('📍 Starting enhanced location detection (inDrive style)...');

//         // Step 1: Get instant location (WiFi positioning)
//         let position;
//         let accuracyType = 'wifi';

//         try {
//           position = await getFastLocation();
//           console.log('📍 Fast location obtained instantly');
//         } catch (fastError) {
//           console.log('📍 Fast location failed, trying GPS...');
//           // Fallback to GPS if fast location fails
//           position = await getGPSLocation();
//           accuracyType = 'gps';
//         }

//         const { latitude, longitude, accuracy } = position.coords;
//         const userLocation = { lat: latitude, lng: longitude };
//         setLocation(userLocation);

//         console.log('📍 Location detected successfully:', {
//           latitude,
//           longitude,
//           accuracy: `${Math.round(accuracy)}m`,
//           accuracyType,
//           deviceType,
//           permissionState,
//           timestamp: new Date().toISOString()
//         });

//         // Validate Lahore area
//         const isInLahoreArea = latitude >= 31.3 && latitude <= 31.7 && longitude >= 74.0 && longitude <= 74.6;
//         if (isInLahoreArea) {
//           console.log('📍 Confirmed: Location is in Lahore area');
//         } else {
//           console.warn('📍 Location coordinates may be outside Lahore area:', { latitude, longitude });
//         }

//         // Get address asynchronously (don't block UI)
//         getAddressFromCoords(latitude, longitude)
//           .then(address => {
//             // Add accuracy and permission indicators
//             let addressWithIndicators = address;
//             if (accuracy > 1000) { // Over 1km accuracy
//               addressWithIndicators += ` (Approximate - ${Math.round(accuracy)}m accuracy)`;
//             } else if (accuracy > 100) { // Good accuracy
//               addressWithIndicators += ` (±${Math.round(accuracy)}m)`;
//             }

//             // Add permission state indicator
//             if (permissionState === 'prompt') {
//               addressWithIndicators += ' • Permission: Pending';
//             } else if (permissionState === 'denied') {
//               addressWithIndicators += ' • Permission: Denied';
//             }

//             setAddress(addressWithIndicators);
//           })
//           .catch(error => {
//             console.error('Error getting address:', error);
//             setAddress(`${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
//           });

//         // Get safety score asynchronously
//         getSafetyScore(userLocation)
//           .then(score => setSafetyScore(score))
//           .catch(error => console.error('Error getting safety score:', error));

//         // Step 2: Try to improve accuracy in background (like inDrive)
//         if (accuracy > 500) { // If accuracy is poor (>500m)
//           console.log('📍 Attempting to improve accuracy in background...');
//           getGPSLocation()
//             .then(gpsPosition => {
//               const { latitude: gpsLat, longitude: gpsLng, accuracy: gpsAccuracy } = gpsPosition.coords;
//               if (gpsAccuracy < accuracy) { // Only update if GPS is more accurate
//                 const improvedLocation = { lat: gpsLat, lng: gpsLng };
//                 setLocation(improvedLocation);
//                 console.log('📍 Location improved with GPS:', `${Math.round(gpsAccuracy)}m accuracy`);

//                 // Update address with improved location
//                 getAddressFromCoords(gpsLat, gpsLng)
//                   .then(address => setAddress(address))
//                   .catch(error => console.error('Error updating address:', error));

//                 // Update safety score with improved location
//                 getSafetyScore(improvedLocation)
//                   .then(score => setSafetyScore(score))
//                   .catch(error => console.error('Error updating safety score:', error));
//               } else {
//                 console.log('📍 GPS accuracy not better than current location');
//               }
//             })
//             .catch(error => console.log('📍 Background GPS improvement failed (normal):', error.message));
//         }

//       } catch (error) {
//         console.log('📍 Location access failed:', error);

//         let errorMessage = 'Unable to get location';
//         if (error.code === error.PERMISSION_DENIED) {
//           errorMessage = 'Location permission denied - Please enable location access in browser settings';
//         } else if (error.code === error.POSITION_UNAVAILABLE) {
//           errorMessage = 'Location unavailable - Check your GPS/WiFi and try again';
//         } else if (error.code === error.TIMEOUT) {
//           errorMessage = 'Location request timeout - Try refreshing the page';
//         }

//         setAddress(errorMessage);

//         // Helpful guidance for users based on permission state
//         if (permissionState === 'denied') {
//           console.log('💡 Permission denied: User must enable location in browser settings');
//         } else if (deviceType === 'desktop') {
//           console.log('💡 Desktop tip: Enable location in browser settings for faster, more accurate detection');
//         } else {
//           console.log('💡 Mobile tip: Enable GPS and location permissions for best accuracy');
//         }
//       }
//     };

//     getEnhancedLocation();
//   }, [deviceType]);

//   // Load user alerts
//   useEffect(() => {
//     if (token) {
//       loadUserAlerts();
//     }
//   }, [token]);

//   // Intersection Observer for animations
//   useEffect(() => {
//     const observer = new IntersectionObserver(
//       ([entry]) => {
//         if (entry.isIntersecting) {
//           setIsVisible(true);
//         }
//       },
//       { threshold: 0.1 }
//     );

//     const element = document.querySelector(`.${styles.quickActionsSection}`);
//     if (element) {
//       observer.observe(element);
//     }

//     return () => observer.disconnect();
//   }, []);

//   // Enhanced address geocoding
//   const getAddressFromCoords = async (lat, lng) => {
//     try {
//       const response = await fetch(
//         `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
//       );
      
//       if (!response.ok) throw new Error('Geocoding failed');
      
//       const data = await response.json();

//       if (data && data.address) {
//         const addr = data.address;
//         const addressParts = [];

//         // Build comprehensive address
//         if (addr.road) addressParts.push(addr.road);
//         if (addr.neighbourhood) addressParts.push(addr.neighbourhood);
//         if (addr.suburb) addressParts.push(addr.suburb);
//         if (addr.city_district) addressParts.push(addr.city_district);
//         if (addr.city) addressParts.push(addr.city);
//         if (addr.state) addressParts.push(addr.state);

//         const fullAddress = addressParts.join(', ');
//         return fullAddress || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
//       }
      
//       return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
//     } catch (error) {
//       console.error('Reverse geocoding error:', error);
//       return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
//     }
//   };

//   // Enhanced safety score calculation
//   const getSafetyScore = async (userLocation) => {
//     try {
//       const areaName = await getAreaFromCoordinates(userLocation.lat, userLocation.lng);

//       if (areaName) {
//         const safetyData = await apiService.getAreaSafetyScore(areaName);

//         return {
//           score: safetyData.safety_score,
//           level: safetyData.risk_level,
//           crimesCount: safetyData.crime_statistics?.total_crimes || 0,
//           highRiskCount: safetyData.crime_statistics?.high_risk_crimes || 0,
//           area: areaName,
//           confidence: safetyData.confidence,
//           source: 'backend'
//         };
//       } else {
//         return await calculateClientSideSafetyScore(userLocation);
//       }
//     } catch (error) {
//       console.error('Error getting safety score from backend:', error);
//       return await calculateClientSideSafetyScore(userLocation);
//     }
//   };

//   // Enhanced helper function to get area name from coordinates with Lahore-specific handling
//   const getAreaFromCoordinates = async (lat, lng) => {
//     try {
//       // First, try multiple geocoding services for better accuracy
//       const geocodingServices = [
//         // Primary: Nominatim with enhanced parameters for Lahore
//         async () => {
//           const response = await fetch(
//             `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1&accept-language=en&extratags=1`
//           );
//           if (!response.ok) throw new Error('Nominatim failed');
//           return response.json();
//         },

//         // Fallback: Photon (Komoot) - better for local areas
//         async () => {
//           const response = await fetch(
//             `https://photon.komoot.io/reverse?lat=${lat}&lon=${lng}&lang=en`
//           );
//           if (!response.ok) throw new Error('Photon failed');
//           const data = await response.json();
//           // Transform Photon response to match Nominatim format
//           if (data.features && data.features[0]) {
//             const feature = data.features[0];
//             return {
//               address: {
//                 neighbourhood: feature.properties.neighbourhood,
//                 suburb: feature.properties.suburb,
//                 city: feature.properties.city,
//                 state: feature.properties.state,
//                 country: feature.properties.country
//               }
//             };
//           }
//           throw new Error('No Photon results');
//         }
//       ];

//       let geocodingData = null;
//       for (const service of geocodingServices) {
//         try {
//           geocodingData = await service();
//           console.log('📍 Geocoding service successful');
//           break;
//         } catch (error) {
//           console.warn('📍 Geocoding service failed:', error.message);
//           continue;
//         }
//       }

//       if (!geocodingData || !geocodingData.address) {
//         console.warn('📍 All geocoding services failed');
//         return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
//       }

//       const addr = geocodingData.address;
//       console.log('📍 Raw geocoding data for Lahore area:', addr);

//       // Lahore-specific neighborhood mapping and prioritization
//       const lahoreNeighborhoods = {
//         // Major Lahore neighborhoods and areas
//         'Model Town': ['model town', 'modeltown'],
//         'Johar Town': ['johartown', 'johar town'],
//         'DHA': ['dha', 'defense housing authority', 'defence housing authority'],
//         'Gulberg': ['gulberg'],
//         'Cantt': ['cantt', 'cantonment'],
//         'Wapda Town': ['wapda town', 'wapdatown'],
//         'Faisal Town': ['faisal town', 'faisaltown'],
//         'Bahria Town': ['bahria town', 'bahriatown'],
//         'Township': ['township', 'lahore township'],
//         'Shadman': ['shadman'],
//         'Anarkali': ['anarkali'],
//         'Mall Road': ['mall road', 'the mall'],
//         'Badami Bagh': ['badami bagh'],
//         'Ichhra': ['ichhra'],
//         'Samanabad': ['samanabad'],
//         'Garhi Shahu': ['garhi shahu'],
//         'Shalimar': ['shalimar'],
//         'Ravi': ['ravi'],
//         'Wagah': ['wagah'],
//         'Allama Iqbal Town': ['allama iqbal town', 'iqbal town'],
//         'Sabzazar': ['sabzazar'],
//         'Valencia Town': ['valencia town', 'valenciatown'],
//         'EME Society': ['eme society', 'eme'],
//         'Askari': ['askari'],
//         'Cavalry Ground': ['cavalry ground'],
//         'LDA Avenue': ['lda avenue', 'lda'],
//         'Lake City': ['lake city'],
//         'Beaconhouse': ['beaconhouse'],
//         'Forman Christian College': ['forman', 'fcc'],
//         'LUMS': ['lums', 'lahore university'],
//         'Punjab University': ['punjab university', 'pu'],
//         'GCU': ['gcu', 'government college'],
//         'King Edward Medical': ['king edward', 'kemc'],
//         'Mayo Hospital': ['mayo hospital'],
//         'Jinnah Hospital': ['jinnah hospital'],
//         'Services Hospital': ['services hospital']
//       };

//       // Function to match neighborhood names
//       const matchNeighborhood = (text) => {
//         if (!text) return null;
//         const lowerText = text.toLowerCase().trim();

//         for (const [neighborhood, aliases] of Object.entries(lahoreNeighborhoods)) {
//           if (aliases.some(alias => lowerText.includes(alias))) {
//             return neighborhood;
//           }
//         }
//         return null;
//       };

//       // Prioritized area extraction for Lahore
//       const prioritizedAreas = [
//         // Most specific - direct neighborhood matches
//         matchNeighborhood(addr.neighbourhood),
//         matchNeighborhood(addr.locality),
//         matchNeighborhood(addr.residential),
//         matchNeighborhood(addr.hamlet),
//         matchNeighborhood(addr.suburb),
//         matchNeighborhood(addr.quarter),
//         matchNeighborhood(addr.ward),
//         matchNeighborhood(addr.borough),
//         matchNeighborhood(addr.city_district),

//         // Raw values if no match found
//         addr.neighbourhood,
//         addr.locality,
//         addr.residential,
//         addr.hamlet,
//         addr.suburb,
//         addr.quarter,
//         addr.ward,
//         addr.borough,
//         addr.city_district
//       ];

//       // Find the most specific non-empty area
//       let specificArea = null;
//       for (const area of prioritizedAreas) {
//         if (area && area.trim() && area.toLowerCase() !== 'punjab' && area.toLowerCase() !== 'lahore') {
//           specificArea = area.trim();
//           console.log('📍 Selected specific Lahore area:', specificArea);
//           break;
//         }
//       }

//       // If we found a specific area, use it
//       if (specificArea) {
//         return specificArea;
//       }

//       // Enhanced fallback: try to build meaningful area names
//       const areaParts = [];

//       // Add road/street if available
//       if (addr.road) {
//         areaParts.push(addr.road);
//       }

//       // Add suburb or locality
//       if (addr.suburb && addr.suburb !== addr.city_district) {
//         areaParts.push(addr.suburb);
//       } else if (addr.locality) {
//         areaParts.push(addr.locality);
//       }

//       if (areaParts.length > 0) {
//         const combined = areaParts.join(', ');
//         console.log('📍 Built area from components:', combined);
//         return combined;
//       }

//       // Last resort: use coordinates with Lahore context
//       const coordinateArea = `Lahore Area (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
//       console.log('📍 Using coordinate-based area:', coordinateArea);
//       return coordinateArea;

//     } catch (error) {
//       console.error('📍 Area detection error:', error);
//       return `Lahore Area (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
//     }
//   };

//   // Fallback client-side safety score calculation
//   const calculateClientSideSafetyScore = async (userLocation) => {
//     try {
//       const crimes = await apiService.getCrimes({
//         latitude: userLocation.lat,
//         longitude: userLocation.lng,
//         radius: 2
//       });

//       if (crimes.length === 0) {
//         return {
//           score: 90,
//           level: 'Very Safe',
//           crimesCount: 0,
//           highRiskCount: 0,
//           source: 'client_calculated'
//         };
//       }

//       let totalRisk = 0;
//       let highRiskCount = 0;

//       crimes.forEach(crime => {
//         const riskWeight = crime.risk_level === 'High' ? 3 : crime.risk_level === 'Medium' ? 2 : 1;
//         totalRisk += riskWeight;
//         if (crime.risk_level === 'High') highRiskCount++;
//       });

//       const avgRisk = totalRisk / crimes.length;
//       let safetyScore = Math.max(10, 100 - (avgRisk * 15 + highRiskCount * 5));

//       let safetyLevel = 'Very Safe';
//       if (safetyScore < 40) safetyLevel = 'High Risk';
//       else if (safetyScore < 60) safetyLevel = 'Moderate Risk';
//       else if (safetyScore < 80) safetyLevel = 'Generally Safe';

//       return {
//         score: Math.round(safetyScore),
//         level: safetyLevel,
//         crimesCount: crimes.length,
//         highRiskCount: highRiskCount,
//         source: 'client_calculated'
//       };
//     } catch (error) {
//       console.error('Error calculating client-side safety score:', error);
//       return {
//         score: 50,
//         level: 'Unknown',
//         crimesCount: 0,
//         highRiskCount: 0,
//         source: 'error_fallback'
//       };
//     }
//   };

//   // Load user alerts
//   const loadUserAlerts = async () => {
//     try {
//       const alerts = await apiService.getUserAlerts(token);
//       setUserAlerts(Array.isArray(alerts) ? alerts : []);
//     } catch (error) {
//       console.error('Error loading alerts:', error);
//     }
//   };

//   // Enhanced location tracking toggle
//   const handleLocationTrackingToggle = async () => {
//     if (!token) {
//       alert('🔐 Please log in to enable location tracking.');
//       return;
//     }

//     setLocationTrackingLoading(true);

//     try {
//       if (locationTrackingEnabled) {
//         await stopLocationTracking();
//         alert('📍 Location tracking disabled.\n\nReal-time monitoring stopped.');
//       } else {
//         if (locationPermission === 'denied') {
//           const guidance = deviceType === 'mobile'
//             ? 'Enable location in browser settings and device settings, then refresh the page.'
//             : 'Allow location access in browser settings.';

//           alert(`📍 Location permission required.\n\n${guidance}`);
//           return;
//         }

//         if (locationPermission === 'prompt') {
//           try {
//             await requestLocationPermission();
//           } catch (error) {
//             alert(`📍 Location permission denied.\n\n${error.message}`);
//             return;
//           }
//         }

//         const result = await startLocationTracking();
        
//         if (result.initialAccuracy) {
//           const accuracyMsg = result.initialAccuracy <= 100 
//             ? 'High accuracy GPS activated!'
//             : result.initialAccuracy <= 500
//             ? 'Good location accuracy achieved.'
//             : 'Location tracking enabled (approximate accuracy).';

//           alert(`📍 ${accuracyMsg}\n\nYour location will be monitored for safety alerts.`);
//         } else {
//           alert('📍 Location tracking enabled!\n\nReal-time monitoring activated.');
//         }
//       }
//     } catch (error) {
//       console.error('Location tracking toggle error:', error);
//       alert(`❌ Failed to ${locationTrackingEnabled ? 'disable' : 'enable'} location tracking: ${error.message}`);
//     } finally {
//       setLocationTrackingLoading(false);
//     }
//   };

//   // Enhanced subscribe to alerts
//   const subscribeToAlerts = async () => {
//     if (!token) {
//       alert('🔐 Please log in to manage alert subscriptions.');
//       return;
//     }

//     try {
//       const isValid = await validateToken();
//       if (!isValid) {
//         alert('🔐 Your session has expired. Please log in again.');
//         logout();
//         return;
//       }
//     } catch (error) {
//       console.error('Token validation error:', error);
//       alert('🔐 Authentication error. Please log in again.');
//       logout();
//       return;
//     }

//     if (!location) {
//       alert('📍 Location access required for alert subscriptions. Please enable location services.');
//       return;
//     }

//     try {
//       setIsLoading(true);

//       let areaName = await getAreaFromCoordinates(location.lat, location.lng);
//       if (!areaName) {
//         areaName = `Area near ${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`;
//       }

//       const notificationTypes = ['email'];
//       if (user?.browser_notifications_enabled && browserPushSupported) {
//         notificationTypes.push('browser');
//       }

//       const subscriptionData = {
//         alert_types: ["crime", "safety", "emergency"],
//         areas: [areaName],
//         radius: Number(user?.alertRadius ?? 5.0),
//         notification_types: notificationTypes,
//         is_active: true
//       };

//       const response = await apiService.subscribeToAlerts(token, subscriptionData);

//       try {
//         const updatedAlerts = await apiService.getUserAlerts(token);
//         setUserAlerts(Array.isArray(updatedAlerts) ? updatedAlerts : []);
//       } catch (alertError) {
//         console.log('⚠️ Could not refresh alerts, but subscription was successful');
//       }

//       alert(`✅ ${response.message}\n\nYou will now receive real-time safety alerts for ${areaName}.`);

//     } catch (error) {
//       console.error('❌ Subscription error:', error);
//       alert(`❌ Failed to subscribe: ${error.message}`);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   // Subscribe with browser push setup
//   const subscribeToAlertsWithBrowserPush = async () => {
//     if (!token) {
//       alert('🔐 Please log in to manage alert subscriptions.');
//       return;
//     }

//     if (browserPushSupported && !user?.browser_notifications_enabled) {
//       const enableBrowserPush = confirm(
//         '🔔 Enable Browser Push Notifications?\n\nGet instant safety alerts directly in your browser even when the tab is closed.\n\nClick OK to setup browser notifications.'
//       );

//       if (enableBrowserPush) {
//         setShowBrowserPushSettings(true);
//         return;
//       }
//     }

//     await subscribeToAlerts();
//   };

//   const unsubscribeFromAlerts = async () => {
//     try {
//       setIsLoading(true);
//       await apiService.unsubscribeFromAlerts(token);
//       setUserAlerts([]);
//       alert('🔕 Successfully unsubscribed from all alerts.');
//     } catch (error) {
//       console.error('Unsubscribe error:', error);
//       alert('❌ Failed to unsubscribe. Please try again.');
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   // Enhanced safety check
//   const performSafetyCheck = async () => {
//     if (!location) {
//       alert('📍 Location access required for safety check.');
//       return;
//     }

//     setIsLoading(true);
//     try {
//       const safetyData = await getSafetyScore(location);
//       setSafetyScore(safetyData);

//       const recentCrimes = await apiService.getCrimes({
//         latitude: location.lat,
//         longitude: location.lng,
//         radius: 2,
//         limit: 10
//       });

//       let safetyMessage = `📍 Your Location: ${address || 'Calculating...'}\n\n`;
//       safetyMessage += `🛡️ Safety Score: ${safetyData.score}% - ${safetyData.level}\n`;

//       if (safetyData.source === 'backend') {
//         safetyMessage += `📊 Data Source: Official Crime Database\n`;
//       } else {
//         safetyMessage += `📊 Data Source: Real-time Analysis\n`;
//       }

//       safetyMessage += `\n`;

//       if (safetyData.crimesCount > 0) {
//         safetyMessage += `⚠️ Crime Statistics:\n`;
//         safetyMessage += `• Total incidents in area: ${safetyData.crimesCount}\n`;
//         safetyMessage += `• High-risk incidents: ${safetyData.highRiskCount}\n\n`;

//         if (recentCrimes.length > 0) {
//           safetyMessage += `📋 Recent crimes:\n`;
//           recentCrimes.slice(0, 3).forEach(crime => {
//             safetyMessage += `• ${crime.crime_type} (${crime.risk_level} risk)\n`;
//           });
//           safetyMessage += `\n`;
//         }
//       } else {
//         safetyMessage += `✅ No recent criminal activity detected\n`;
//         safetyMessage += `🟢 Area appears to be safe\n\n`;
//       }

//       safetyMessage += `💡 Safety Tips:\n`;
//       if (safetyData.score < 40) {
//         safetyMessage += `• Stay alert and aware of surroundings\n`;
//         safetyMessage += `• Avoid walking alone at night\n`;
//         safetyMessage += `• Keep emergency contacts handy\n`;
//         safetyMessage += `• Consider alternative routes\n`;
//       } else if (safetyData.score < 60) {
//         safetyMessage += `• Maintain normal safety precautions\n`;
//         safetyMessage += `• Stay in well-lit areas at night\n`;
//         safetyMessage += `• Keep valuables secure\n`;
//       } else {
//         safetyMessage += `• Continue normal activities\n`;
//         safetyMessage += `• Remain aware of surroundings\n`;
//         safetyMessage += `• Report any suspicious activity\n`;
//       }

//       safetyMessage += `\n🕒 Last updated: ${new Date().toLocaleTimeString()}`;
//       safetyMessage += `\n📱 Device: ${deviceType}`;

//       alert(safetyMessage);

//     } catch (error) {
//       console.error('Safety check error:', error);
//       alert('❌ Could not perform safety check. Please try again.');
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   // Enhanced emergency directions
//   const getEmergencyDirections = async (serviceType) => {
//     if (!location) {
//       alert('📍 Location access required for directions.');
//       return;
//     }

//     const services = {
//       police: {
//         name: 'Nearest Police Station',
//         search: 'police station',
//         icon: 'fas fa-shield-alt'
//       },
//       hospital: {
//         name: 'Nearest Hospital',
//         search: 'hospital',
//         icon: 'fas fa-hospital'
//       },
//       fire: {
//         name: 'Nearest Fire Station',
//         search: 'fire station',
//         icon: 'fas fa-fire-extinguisher'
//       },
//       pharmacy: {
//         name: 'Nearest Pharmacy',
//         search: 'pharmacy',
//         icon: 'fas fa-prescription-bottle'
//       }
//     };

//     const service = services[serviceType];
//     if (!service) return;

//     try {
//       const mapUrl = `https://www.google.com/maps/dir/?api=1&origin=${location.lat},${location.lng}&destination=${service.search}&travelmode=driving`;
//       window.open(mapUrl, '_blank');

//       alert(`🗺️ Opening directions to ${service.name}\n\nYour route is being calculated...`);

//     } catch (error) {
//       console.error('Directions error:', error);
//       alert('❌ Could not open directions. Please try again.');
//     }
//   };

//   const actions = [
//     {
//       id: 'safety-check',
//       icon: 'fas fa-shield-alt',
//       label: 'Safety Check',
//       description: 'Get real-time safety assessment of your current location',
//       color: '#059669',
//       gradient: 'linear-gradient(135deg, #059669, #047857)',
//       type: 'safety',
//       action: performSafetyCheck
//     },
//     {
//       id: 'live-alerts',
//       icon: 'fas fa-bell',
//       label: userAlerts.length > 0 ? 'Manage Alerts' : 'Subscribe to Alerts',
//       description: userAlerts.length > 0
//         ? 'Manage your crime and safety alert subscriptions'
//         : 'Get real-time crime and safety alerts in your area',
//       color: '#f59e0b',
//       gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
//       type: 'alert',
//       action: userAlerts.length > 0 ? unsubscribeFromAlerts : subscribeToAlertsWithBrowserPush
//     },
//     {
//       id: 'safety-resources',
//       icon: 'fas fa-first-aid',
//       label: 'Emergency Resources',
//       description: 'Get directions to nearest emergency services',
//       color: '#0891b2',
//       gradient: 'linear-gradient(135deg, #0891b2, #0e7490)',
//       type: 'resource',
//       action: () => {
//         const serviceOptions =
//           `🚓 Police Station (1)\n` +
//           `🏥 Hospital/Emergency (2)\n` +
//           `🚒 Fire Department (3)\n` +
//           `💊 Pharmacy (4)\n\n` +
//           `Enter the service number (1-4):`;

//         const choice = prompt(`🛡️ Emergency Services Directions\n\n${serviceOptions}`);

//         if (choice) {
//           const services = {
//             '1': 'police', 'police': 'police',
//             '2': 'hospital', 'hospital': 'hospital',
//             '3': 'fire', 'fire': 'fire',
//             '4': 'pharmacy', 'pharmacy': 'pharmacy'
//           };

//           const serviceType = services[choice.toLowerCase()];
//           if (serviceType) {
//             getEmergencyDirections(serviceType);
//           } else {
//             alert('❌ Please select a valid service (1-4)');
//           }
//         }
//       }
//     },
//     {
//       id: 'route-safety',
//       icon: 'fas fa-route',
//       label: 'Route Safety',
//       description: 'Plan safe routes and check area safety',
//       color: '#7c3aed',
//       gradient: 'linear-gradient(135deg, #7c3aed, #6d28d9)',
//       type: 'navigation',
//       action: () => {
//         const destination = prompt('🗺️ Route Safety Check\n\nEnter your destination address:');
//         if (destination) {
//           const mapUrl = `https://www.google.com/maps/dir/?api=1&origin=${location?.lat},${location?.lng}&destination=${encodeURIComponent(destination)}&travelmode=driving`;
//           window.open(mapUrl, '_blank');

//           alert(`📍 Route Planning Started\n\nFrom: ${address || 'Your location'}\nTo: ${destination}\n\n✅ Safe route suggestions will be shown on map`);
//         }
//       }
//     }
//   ];

//   const handleActionClick = (action) => {
//     if (isLoading) return;

//     setActiveAction(action.id);

//     if (navigator.vibrate) {
//       navigator.vibrate(50);
//     }

//     action.action();

//     setTimeout(() => setActiveAction(null), 600);
//   };

//   const getActionBadge = (type) => {
//     const badges = {
//       safety: { text: 'LIVE', color: '#10b981' },
//       alert: { text: 'ALERTS', color: '#f59e0b' },
//       resource: { text: 'EMERGENCY', color: '#dc2626' },
//       navigation: { text: 'ROUTES', color: '#7c3aed' }
//     };

//     return badges[type] || { text: 'ACTION', color: '#6b7280' };
//   };

//   const showBrowserPushPrompt = browserPushSupported && !user?.browser_notifications_enabled;

//   return (
//     <section className={`${styles.quickActionsSection} ${isVisible ? styles.visible : ''}`}>
//       <div className={styles.container}>
//         {/* Browser Push Setup Prompt */}
//         {showBrowserPushPrompt && (
//           <div className={styles.browserPushPrompt}>
//             <div className={styles.browserPushPromptContent}>
//               <i className="fas fa-bell"></i>
//               <div className={styles.browserPushPromptText}>
//                 <h4>Enable Browser Notifications</h4>
//                 <p>Get instant safety alerts directly in your browser</p>
//               </div>
//               <button
//                 onClick={() => setShowBrowserPushSettings(true)}
//                 className={styles.setupButton}
//               >
//                 Enable
//               </button>
//             </div>
//           </div>
//         )}

//         {/* Enhanced Location Tracking Toggle */}
//         {token && (
//           <div className={styles.locationTrackingSection}>
//             <LocationTrackingToggle
//               isEnabled={locationTrackingEnabled}
//               onToggle={handleLocationTrackingToggle}
//               permission={locationPermission}
//               status={locationTrackingStatus}
//               loading={locationTrackingLoading}
//               deviceType={deviceType}
//             />
//           </div>
//         )}

//         {/* Header */}
//         <div className={styles.header}>
//           <div className={styles.badge}>
//             <i className="fas fa-bolt"></i>
//             <span>Enhanced Safety Tools</span>
//           </div>
//           <h2 className={styles.title}>Real-time Safety Features</h2>
//           <p className={styles.subtitle}>
//             Advanced location tracking and emergency resources for {deviceType} devices
//           </p>
//         </div>

//         {/* Actions Grid */}
//         <div className={styles.grid}>
//           {actions.map((action, index) => {
//             const badge = getActionBadge(action.type);

//             return (
//               <div
//                 key={action.id}
//                 className={`${styles.card} ${activeAction === action.id ? styles.active : ''} ${isLoading ? styles.loading : ''}`}
//                 style={{
//                   '--action-color': action.color,
//                   '--action-gradient': action.gradient,
//                   animationDelay: `${index * 100}ms`
//                 }}
//                 onClick={() => handleActionClick(action)}
//               >
//                 {isLoading && activeAction === action.id && (
//                   <div className={styles.loadingOverlay}>
//                     <div className={styles.loadingSpinner}>
//                       <i className="fas fa-spinner fa-spin"></i>
//                     </div>
//                   </div>
//                 )}

//                 <div className={styles.background}>
//                   <div className={styles.orb}></div>
//                   <div className={styles.glow}></div>
//                 </div>

//                 <div
//                   className={styles.actionBadge}
//                   style={{ backgroundColor: badge.color }}
//                 >
//                   {badge.text}
//                 </div>

//                 <div className={styles.iconContainer}>
//                   <div
//                     className={styles.iconWrapper}
//                     style={{ background: action.gradient }}
//                   >
//                     <i className={action.icon}></i>
//                   </div>
//                 </div>

//                 <div className={styles.content}>
//                   <h3 className={styles.label}>{action.label}</h3>
//                   <p className={styles.description}>{action.description}</p>

//                   {action.id === 'safety-check' && safetyScore && (
//                     <div className={styles.safetyInfo}>
//                       <span className={styles.safetyScore}>
//                         {safetyScore.score}% Safe
//                       </span>
//                       <span className={styles.safetyLevel}>
//                         {safetyScore.level}
//                       </span>
//                       {safetyScore.source === 'backend' && (
//                         <span className={styles.safetySource}>
//                           Official Data
//                         </span>
//                       )}
//                     </div>
//                   )}

//                   {action.id === 'live-alerts' && userAlerts.length > 0 && (
//                     <div className={styles.alertInfo}>
//                       <span className={styles.alertCount}>
//                         {userAlerts.length} Active
//                       </span>
//                     </div>
//                   )}
//                 </div>

//                 <div className={styles.arrow}>
//                   <i className="fas fa-chevron-right"></i>
//                 </div>
//               </div>
//             );
//           })}
//         </div>

//         {/* Enhanced Status Footer */}
//         <div className={styles.footer}>
//           <div className={styles.statusGrid}>
//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className="fas fa-shield-check"></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Safety Status</span>
//                 <span className={styles.statusValue}>
//                   {safetyScore ? `${safetyScore.score}% - ${safetyScore.level}` : 'Checking...'}
//                 </span>
//               </div>
//             </div>

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className={`fas ${location ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Location</span>
//                 <span className={styles.statusValue}>
//                   {location ? 'Active' : 'Required'}
//                 </span>
//               </div>
//             </div>

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className="fas fa-bell"></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Alerts</span>
//                 <span className={styles.statusValue}>
//                   {userAlerts.length} Active
//                 </span>
//               </div>
//             </div>

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className={`fas ${user?.browser_notifications_enabled ? 'fa-bell' : 'fa-bell-slash'}`}></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Browser Alerts</span>
//                 <span className={styles.statusValue}>
//                   {user?.browser_notifications_enabled ? 'Enabled' : browserPushSupported ? 'Available' : 'Unsupported'}
//                 </span>
//               </div>
//             </div>

//             {token && (
//               <div className={styles.statusItem}>
//                 <div className={styles.statusIcon}>
//                   <i className={`fas ${locationTrackingEnabled ? 'fa-location-arrow' : 'fa-location-crosshairs'}`}></i>
//                 </div>
//                 <div className={styles.statusContent}>
//                   <span className={styles.statusLabel}>Location Tracking</span>
//                   <span className={styles.statusValue}>
//                     {locationTrackingEnabled ? 'Active' : 'Inactive'}
//                   </span>
//                 </div>
//               </div>
//             )}

//             <div className={styles.statusItem}>
//               <div className={styles.statusIcon}>
//                 <i className={`fas fa-${deviceType}`}></i>
//               </div>
//               <div className={styles.statusContent}>
//                 <span className={styles.statusLabel}>Device</span>
//                 <span className={styles.statusValue}>
//                   {deviceType.charAt(0).toUpperCase() + deviceType.slice(1)}
//                 </span>
//               </div>
//             </div>
//           </div>

//           {address && (
//             <div className={styles.locationInfo}>
//               <i className="fas fa-map-marker-alt"></i>
//               <span>{address}</span>
//               {deviceType === 'desktop' && (
//                 <span className={styles.locationNote}>(WiFi positioning)</span>
//               )}
//             </div>
//           )}
//         </div>
//       </div>

//       {showBrowserPushSettings && (
//         <div className={styles.modalOverlay}>
//           <div className={styles.modalContent}>
//             <BrowserPushSettings
//               user={user}
//               token={token}
//               onUpdate={() => window.location.reload()}
//               onClose={() => setShowBrowserPushSettings(false)}
//             />
//           </div>
//         </div>
//       )}
//     </section>
//   );
// };

// export default QuickActions;







import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import BrowserPushSettings from '../UserDashboard/BrowserNotifications';
import styles from '../UserDashboard/QuickActions.module.css';

const QuickActions = ({ dashboardStats, dashboardAlerts, userLocation }) => {
const { user, token, validateToken, logout } = useAuth(); 
  const [activeAction, setActiveAction] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [location, setLocation] = useState(null);
  const [address, setAddress] = useState('');
  const [safetyScore, setSafetyScore] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userAlerts, setUserAlerts] = useState([]);
  const [showBrowserPushSettings, setShowBrowserPushSettings] = useState(false);
  const [browserPushSupported, setBrowserPushSupported] = useState(false);
  const [currentAccuracy, setCurrentAccuracy] = useState(null);
  const [isManualLocation, setIsManualLocation] = useState(false);
  const [showLocationInput, setShowLocationInput] = useState(false);
  const [deviceType, setDeviceType] = useState('Desktop');

  // Sync with dashboard data from props
  useEffect(() => {
    if (dashboardStats) {
      setSafetyScore({
        score: dashboardStats.safety_score,
        level: dashboardStats.risk_level,
        crimesCount: dashboardStats.total_crimes || 0,
        highRiskCount: dashboardStats.high_risk_crimes || 0,
        area: dashboardStats.area,
        source: 'dashboard'
      });
    }
  }, [dashboardStats]);

  useEffect(() => {
    if (dashboardAlerts) {
      setUserAlerts(dashboardAlerts);
    }
  }, [dashboardAlerts]);

  useEffect(() => {
    if (userLocation && !isManualLocation) {
      setLocation(userLocation);
    }
  }, [userLocation, isManualLocation]);

  // Lahore-restricted geocoding function
  const geocodeLocationInLahore = async (locationName) => {
    try {
      // Use Nominatim with Lahore restriction
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?` +
        `q=${encodeURIComponent(locationName)},Lahore,Pakistan` +
        `&format=json` +
        `&countrycodes=pk` + // Restrict to Pakistan
        `&limit=5` + // Get multiple results to filter for Lahore
        `&addressdetails=1`,
        { signal: AbortSignal.timeout(10000) }
      );

      if (!response.ok) {
        throw new Error('Geocoding failed');
      }

      const data = await response.json();
      
      if (data && data.length > 0) {
        const normalizedQuery = locationName.toLowerCase().trim();
        const queryTokens = normalizedQuery.split(/\s+/).filter(token => token.length > 1);

        // Filter results to only include Lahore locations
        const lahoreResults = data.filter(result => {
          const lat = parseFloat(result.lat);
          const lng = parseFloat(result.lon);
          // Lahore bounds: roughly 31.3-31.7 N, 74.0-74.6 E
          return lat >= 31.3 && lat <= 31.7 && lng >= 74.0 && lng <= 74.6;
        });

        if (lahoreResults.length === 0) {
          throw new Error('Location not found in Lahore');
        }

        // Prefer results that match the user-entered area text.
        const scoredResults = lahoreResults
          .map(result => {
            const text = [
              result.display_name,
              result.address?.suburb,
              result.address?.neighbourhood,
              result.address?.road,
              result.address?.quarter,
              result.address?.city_district
            ].filter(Boolean).join(' ').toLowerCase();

            let score = 0;
            if (text.includes(normalizedQuery)) score += 80;
            for (const token of queryTokens) {
              if (text.includes(token)) score += 12;
            }

            return { result, score };
          })
          .sort((a, b) => b.score - a.score);

        const result = scoredResults[0].result;
        return {
          lat: parseFloat(result.lat),
          lng: parseFloat(result.lon),
          displayName: result.display_name,
          address: result.address
        };
      }
      
      throw new Error('Location not found in Lahore');
    } catch (error) {
      console.error('Geocoding error:', error);
      throw error;
    }
  };

  // Handle manual location input
  const handleManualLocationInput = async () => {
    const locationName = prompt(
      '📍 Enter Location Name in Lahore\n\n' +
      'Enter a location in Lahore (e.g., "Egerton Road", "Model Town", "Gulberg"):\n\n' +
      'The system will automatically find the correct coordinates in Lahore.'
    );

    if (!locationName || !locationName.trim()) {
      return;
    }

    try {
      setIsLoading(true);
      setAddress('Searching for location in Lahore...');

      // Geocode the location name (Lahore-restricted)
      const geocodedLocation = await geocodeLocationInLahore(locationName.trim());
      
      // Update location state
      setLocation({
        lat: geocodedLocation.lat,
        lng: geocodedLocation.lng
      });
      
      setIsManualLocation(true);
      setCurrentAccuracy(null); // No GPS accuracy for manual location
      
      // Get clean address
      const cleanAddress = await getAddressFromCoords(geocodedLocation.lat, geocodedLocation.lng);
      setAddress(cleanAddress);
      
      // Get safety score for new location
      const score = await getSafetyScore({
        lat: geocodedLocation.lat,
        lng: geocodedLocation.lng
      });
      setSafetyScore(score);
      
      alert(
        `✅ Location Updated!\n\n` +
        `📍 ${cleanAddress}\n` +
        `🌍 Coordinates: ${geocodedLocation.lat.toFixed(4)}, ${geocodedLocation.lng.toFixed(4)}\n\n` +
        `Safety score and all dashboard data will now use this location.`
      );
      
      // Trigger dashboard refresh by dispatching custom event
      window.dispatchEvent(new CustomEvent('locationUpdated', {
        detail: {
          lat: geocodedLocation.lat,
          lng: geocodedLocation.lng,
          address: cleanAddress,
          isManual: true,
          requestedArea: locationName.trim()
        }
      }));
      
    } catch (error) {
      console.error('Manual location input error:', error);
      alert(
        `❌ Location Not Found\n\n` +
        `Could not find "${locationName}" in Lahore.\n\n` +
        `Please try:\n` +
        `• Using a more specific name\n` +
        `• Including area name (e.g., "Egerton Road", "Model Town")\n` +
        `• Checking spelling`
      );
      
      // Restore previous address if geocoding failed
      if (location) {
        const previousAddress = await getAddressFromCoords(location.lat, location.lng);
        setAddress(previousAddress);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Detect device type
  useEffect(() => {
    const ua = navigator.userAgent;
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
      setDeviceType('Tablet');
    } else if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/.test(ua)) {
      setDeviceType('Mobile');
    } else {
      setDeviceType('Desktop');
    }
  }, []);

  // Function to get current GPS position
  const getCurrentPosition = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const userLocation = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };
          setLocation(userLocation);
          setCurrentAccuracy(position.coords.accuracy);
          setIsManualLocation(false); // Reset manual location flag
          
          // Get address from coordinates
          try {
            const address = await getAddressFromCoords(userLocation.lat, userLocation.lng);
            setAddress(address);
            
            // Get safety score for this location
            const score = await getSafetyScore(userLocation);
            setSafetyScore(score);
          } catch (error) {
            console.error('Error getting address:', error);
            setAddress('Address not available');
          }
        },
        (error) => {
          console.log('Location access denied:', error);
          setAddress('Location access denied');
        }
      );
    }
  }, []);

  // Load user alerts
  useEffect(() => {
    if (token) {
      loadUserAlerts();
    }
  }, [token]);

  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1 }
    );

    const element = document.querySelector(`.${styles.quickActionsSection}`);
    if (element) {
      observer.observe(element);
    }

    return () => observer.disconnect();
  }, []);

  // Get address from coordinates using reverse geocoding
  const getAddressFromCoords = async (lat, lng) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
      );
      const data = await response.json();
      
      if (data && data.address) {
        const addr = data.address;
        // Build complete address hierarchy
        const addressParts = [];
        
        // Add all relevant address components in order
        if (addr.neighbourhood) addressParts.push(addr.neighbourhood);
        if (addr.suburb) addressParts.push(addr.suburb);
        if (addr.city_district) addressParts.push(addr.city_district);
        if (addr.district && addr.district !== addr.city_district) addressParts.push(addr.district);
        if (addr.county && addr.county !== addr.district) addressParts.push(addr.county);
        if (addr.state) addressParts.push(addr.state);
        if (addr.country) addressParts.push(addr.country);
        
        // Return formatted address or fallback
        return addressParts.length > 0 ? addressParts.join(', ') : 'Address not available';
      }
      return 'Address not available';
    } catch (error) {
      console.error('Reverse geocoding error:', error);
      return 'Address not available';
    }
  };

  // Get safety score based on crime data
  // Updated getSafetyScore function in QuickActions.jsx
const getSafetyScore = async (userLocation) => {
  try {
    // First, try to get the area name from coordinates
    const areaName = await getAreaFromCoordinates(userLocation.lat, userLocation.lng);
    
    if (areaName) {
      // Use the backend safety score API
      const safetyData = await apiService.getAreaSafetyScore(areaName);
      
      return {
        score: safetyData.safety_score,
        level: safetyData.risk_level,
        crimesCount: safetyData.crime_statistics?.total_crimes || 0,
        highRiskCount: safetyData.crime_statistics?.high_risk_crimes || 0,
        area: areaName,
        confidence: safetyData.confidence,
        source: 'backend'
      };
    } else {
      // Fallback to client-side calculation if area not found
      return await calculateClientSideSafetyScore(userLocation);
    }
  } catch (error) {
    console.error('Error getting safety score from backend:', error);
    // Fallback to client-side calculation
    return await calculateClientSideSafetyScore(userLocation);
  }
};

// Helper function to get area name from coordinates
// Improved function to get more specific area name from coordinates
const getAreaFromCoordinates = async (lat, lng) => {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
      { signal: AbortSignal.timeout(5000) }
    );
    
    if (!response.ok) {
      console.warn('Nominatim API returned status:', response.status);
      return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }
    
    const data = await response.json();
    
    if (data && data.address) {
      const addr = data.address;
      
      const areaHierarchy = [
        addr.neighbourhood,
        addr.suburb,
        addr.city_district,
        addr.district,
        addr.city,
        addr.town,
        addr.village,
        addr.municipality,
        addr.county,
        addr.state
      ];
      
      const specificArea = areaHierarchy.find(area => 
        area && area.trim() !== '' && area !== 'Punjab'
      );
      
      if (specificArea) {
        console.log('📍 Found specific area:', specificArea);
        return specificArea;
      }
      
      if (addr.road || addr.suburb) {
        const builtArea = [addr.road, addr.suburb].filter(Boolean).join(', ');
        if (builtArea) {
          console.log('📍 Built area from address parts:', builtArea);
          return builtArea;
        }
      }
    }
    
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    
  } catch (error) {
    console.warn('Reverse geocoding unavailable, using coordinates:', error.message);
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
};
// Fallback client-side safety score calculation
const calculateClientSideSafetyScore = async (userLocation) => {
  try {
    const crimes = await apiService.getCrimes({
      latitude: userLocation.lat,
      longitude: userLocation.lng,
      radius: 2 // 2km radius
    });

    if (crimes.length === 0) {
      return { 
        score: 90, 
        level: 'Very Safe', 
        crimesCount: 0,
        highRiskCount: 0,
        source: 'client_calculated'
      };
    }

    let totalRisk = 0;
    let highRiskCount = 0;
    
    crimes.forEach(crime => {
      const riskWeight = crime.risk_level === 'High' ? 3 : crime.risk_level === 'Medium' ? 2 : 1;
      totalRisk += riskWeight;
      if (crime.risk_level === 'High') highRiskCount++;
    });

    const avgRisk = totalRisk / crimes.length;
    let safetyScore = Math.max(10, 100 - (avgRisk * 15 + highRiskCount * 5));
    
    let safetyLevel = 'Very Safe';
    if (safetyScore < 40) safetyLevel = 'High Risk';
    else if (safetyScore < 60) safetyLevel = 'Moderate Risk';
    else if (safetyScore < 80) safetyLevel = 'Generally Safe';
    
    return {
      score: Math.round(safetyScore),
      level: safetyLevel,
      crimesCount: crimes.length,
      highRiskCount: highRiskCount,
      source: 'client_calculated'
    };
  } catch (error) {
    console.error('Error calculating client-side safety score:', error);
    return { 
      score: 50, 
      level: 'Unknown', 
      crimesCount: 0, 
      highRiskCount: 0,
      source: 'error_fallback'
    };
  }
};

  // Load user alerts
  const loadUserAlerts = async () => {
    try {
      const alerts = await apiService.getUserAlerts(token);
      setUserAlerts(Array.isArray(alerts) ? alerts : []);
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };


  // Enhanced subscribe to alerts with real location
  const subscribeToAlerts = async () => {
    if (!token) {
      alert('🔐 Please log in to manage alert subscriptions.');
      return;
    }

    try {
      const isValid = await validateToken();
      if (!isValid) {
        alert('🔐 Your session has expired. Please log in again.');
        logout();
        return;
      }
    } catch (error) {
      console.error('Token validation error:', error);
      alert('🔐 Authentication error. Please log in again.');
      logout();
      return;
    }

    if (!location) {
      alert('📍 Real location access required for alert subscriptions. Please enable location services.');
      return;
    }

    try {
      setIsLoading(true);

      let areaName = await getAreaFromCoordinates(location.lat, location.lng);
      if (!areaName) {
        areaName = `Area near ${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`;
      }

      const notificationTypes = ['email'];
      if (user?.browser_notifications_enabled && browserPushSupported) {
        notificationTypes.push('browser');
      }

      const subscriptionData = {
        alert_types: ["crime", "safety", "emergency"],
        areas: [areaName],
        radius: Number(user?.alertRadius ?? 5.0),
        notification_types: notificationTypes,
        is_active: true,
        location_accuracy: currentAccuracy,
        // location_source: locationSource
      };

      const response = await apiService.subscribeToAlerts(token, subscriptionData);

      try {
        const updatedAlerts = await apiService.getUserAlerts(token);
        setUserAlerts(Array.isArray(updatedAlerts) ? updatedAlerts : []);
      } catch (alertError) {
        console.log('⚠️ Could not refresh alerts, but subscription was successful');
      }

      alert(`✅ ${response.message}\n\nYou will now receive real-time safety alerts for ${areaName}.\n\nLocation accuracy: ${Math.round(currentAccuracy)}m`);

    } catch (error) {
      console.error('❌ Subscription error:', error);
      alert(`❌ Failed to subscribe: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Subscribe with browser push setup
  const subscribeToAlertsWithBrowserPush = async () => {
    if (!token) {
      alert('🔐 Please log in to manage alert subscriptions.');
      return;
    }

    if (browserPushSupported && !user?.browser_notifications_enabled) {
      const enableBrowserPush = confirm(
        '🔔 Enable Browser Push Notifications?\n\nGet instant safety alerts directly in your browser even when the tab is closed.\n\nClick OK to setup browser notifications.'
      );

      if (enableBrowserPush) {
        setShowBrowserPushSettings(true);
        return;
      }
    }

    await subscribeToAlerts();
  };

  const unsubscribeFromAlerts = async () => {
    try {
      setIsLoading(true);
      await apiService.unsubscribeFromAlerts(token);
      setUserAlerts([]);
      alert('🔕 Successfully unsubscribed from all alerts.');
    } catch (error) {
      console.error('Unsubscribe error:', error);
      alert('❌ Failed to unsubscribe. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Enhanced safety check with real location
  const performSafetyCheck = async () => {
    if (!location) {
      alert('📍 Real location access required for safety check.');
      return;
    }

    setIsLoading(true);
    try {
      const safetyData = await getSafetyScore(location);
      setSafetyScore(safetyData);

      const recentCrimes = await apiService.getCrimes({
        latitude: location.lat,
        longitude: location.lng,
        radius: 2,
        limit: 10
      });

      let safetyMessage = `📍 Your REAL Location: ${address || 'Calculating...'}\n\n`;
      safetyMessage += `🛡️ Safety Score: ${safetyData.score}% - ${safetyData.level}\n`;
      // safetyMessage += `🎯 Location Accuracy: ${Math.round(currentAccuracy)}m\n`;
      // safetyMessage += `📱 Device: ${deviceType}\n`;

      if (safetyData.source === 'backend') {
        safetyMessage += `📊 Data Source: Official Crime Database\n`;
      } else {
        safetyMessage += `📊 Data Source: Real-time Analysis\n`;
      }

      safetyMessage += `\n`;

      if (safetyData.crimesCount > 0) {
        safetyMessage += `⚠️ Crime Statistics:\n`;
        safetyMessage += `• Total incidents in area: ${safetyData.crimesCount}\n`;
        safetyMessage += `• High-risk incidents: ${safetyData.highRiskCount}\n\n`;

        if (recentCrimes.length > 0) {
          safetyMessage += `📋 Recent crimes:\n`;
          recentCrimes.slice(0, 3).forEach(crime => {
            safetyMessage += `• ${crime.crime_type} (${crime.risk_level} risk)\n`;
          });
          safetyMessage += `\n`;
        }
      } else {
        safetyMessage += `✅ No recent criminal activity detected\n`;
        safetyMessage += `🟢 Area appears to be safe\n\n`;
      }

      safetyMessage += `💡 Safety Tips:\n`;
      if (safetyData.score < 40) {
        safetyMessage += `• Stay alert and aware of surroundings\n`;
        safetyMessage += `• Avoid walking alone at night\n`;
        safetyMessage += `• Keep emergency contacts handy\n`;
        safetyMessage += `• Consider alternative routes\n`;
      } else if (safetyData.score < 60) {
        safetyMessage += `• Maintain normal safety precautions\n`;
        safetyMessage += `• Stay in well-lit areas at night\n`;
        safetyMessage += `• Keep valuables secure\n`;
      } else {
        safetyMessage += `• Continue normal activities\n`;
        safetyMessage += `• Remain aware of surroundings\n`;
        safetyMessage += `• Report any suspicious activity\n`;
      }

      safetyMessage += `\n🕒 Last updated: ${new Date().toLocaleTimeString()}`;

      alert(safetyMessage);

    } catch (error) {
      console.error('Safety check error:', error);
      alert('❌ Could not perform safety check. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Enhanced emergency directions with real location
  const getEmergencyDirections = async (serviceType) => {
    if (!location) {
      alert('📍 Real location access required for directions.');
      return;
    }

    const services = {
      police: {
        name: 'Nearest Police Station',
        search: 'police station',
        icon: 'fas fa-shield-alt'
      },
      hospital: {
        name: 'Nearest Hospital',
        search: 'hospital',
        icon: 'fas fa-hospital'
      },
      fire: {
        name: 'Nearest Fire Station',
        search: 'fire station',
        icon: 'fas fa-fire-extinguisher'
      },
      pharmacy: {
        name: 'Nearest Pharmacy',
        search: 'pharmacy',
        icon: 'fas fa-prescription-bottle'
      }
    };

    const service = services[serviceType];
    if (!service) return;

    try {
      const mapUrl = `https://www.google.com/maps/dir/?api=1&origin=${location.lat},${location.lng}&destination=${service.search}&travelmode=driving`;
      window.open(mapUrl, '_blank');

      alert(`🗺️ Opening directions to ${service.name}\n\nFrom your current real location.\n\nYour route is being calculated...`);

    } catch (error) {
      console.error('Directions error:', error);
      alert('❌ Could not open directions. Please try again.');
    }
  };

  const actions = [
    {
      id: 'safety-check',
      icon: 'fas fa-shield-alt',
      label: 'Safety Check',
      description: 'Get real-time safety assessment of your actual location',
      color: '#059669',
      gradient: 'linear-gradient(135deg, #059669, #047857)',
      type: 'safety',
      action: performSafetyCheck
    },
    {
      id: 'live-alerts',
      icon: 'fas fa-bell',
      label: userAlerts.length > 0 ? 'Manage Alerts' : 'Subscribe to Alerts',
      description: userAlerts.length > 0
        ? 'Manage your crime and safety alert subscriptions'
        : 'Get real-time crime and safety alerts in your area',
      color: '#f59e0b',
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      type: 'alert',
      action: userAlerts.length > 0 ? unsubscribeFromAlerts : subscribeToAlertsWithBrowserPush
    },
    {
      id: 'safety-resources',
      icon: 'fas fa-first-aid',
      label: 'Emergency Resources',
      description: 'Get directions to nearest emergency services from your location',
      color: '#dc2626',
      gradient: 'linear-gradient(135deg, #dc2626, #b91c1c)',
      type: 'resource',
      action: () => {
        const serviceOptions =
          `🚓 Police Station (1)\n` +
          `🏥 Hospital/Emergency (2)\n` +
          `🚒 Fire Department (3)\n` +
          `💊 Pharmacy (4)\n\n` +
          `Enter the service number (1-4):`;

        const choice = prompt(`🛡️ Emergency Services Directions\n\n${serviceOptions}`);

        if (choice) {
          const services = {
            '1': 'police', 'police': 'police',
            '2': 'hospital', 'hospital': 'hospital',
            '3': 'fire', 'fire': 'fire',
            '4': 'pharmacy', 'pharmacy': 'pharmacy'
          };

          const serviceType = services[choice.toLowerCase()];
          if (serviceType) {
            getEmergencyDirections(serviceType);
          } else {
            alert('❌ Please select a valid service (1-4)');
          }
        }
      }
    }
  ];

  const handleActionClick = (action) => {
    if (isLoading) return;

    setActiveAction(action.id);

    if (navigator.vibrate) {
      navigator.vibrate(50);
    }

    action.action();

    setTimeout(() => setActiveAction(null), 600);
  };

  const getActionBadge = (type) => {
    const badges = {
       safety: { text: 'LIVE', color: '#10b981' },
      alert: { text: 'ALERTS', color: '#f59e0b' },
      resource: { text: 'EMERGENCY', color: '#dc2626' },
      navigation: { text: 'ROUTES', color: '#7c3aed' }
    };

    return badges[type] || { text: 'ACTION', color: '#6b7280' };
  };

  const showBrowserPushPrompt = browserPushSupported && !user?.browser_notifications_enabled;
  const hasValidSafetyScore = typeof safetyScore?.score === 'number' && Number.isFinite(safetyScore.score);
  const normalizedRiskBand = (value) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized.includes('critical') || normalized.includes('avoid')) return 'Avoid';
    if (normalized.includes('high') || normalized.includes('warning')) return 'Warning';
    if (normalized.includes('moderate') || normalized.includes('medium') || normalized.includes('caution')) return 'Caution';
    if (normalized.includes('low') || normalized.includes('safe')) return 'Safe';
    return 'Caution';
  };


  return (
    <section className={`${styles.quickActionsSection} ${isVisible ? styles.visible : ''}`}>
      <div className={styles.container}>
        {/* Browser Push Setup Prompt */}
        {showBrowserPushPrompt && (
          <div className={styles.browserPushPrompt}>
            <div className={styles.browserPushPromptContent}>
              <i className="fas fa-bell"></i>
              <div className={styles.browserPushPromptText}>
                <h4>Enable Browser Notifications</h4>
                <p>Get instant safety alerts directly in your browser</p>
              </div>
              <button
                onClick={() => setShowBrowserPushSettings(true)}
                className={styles.setupButton}
              >
                Enable
              </button>
            </div>
          </div>
        )}
{/* 
        Risk Alerts Display
        {isHighRiskArea && (
          <div className={styles.riskAlertBanner}>
            <div className={styles.riskAlertContent}>
              <i className="fas fa-exclamation-triangle"></i>
              <div className={styles.riskAlertText}>
                <h4>High Risk Area Detected</h4>
                <p>Safety score: {safetyScore?.score}% - {safetyScore?.level}</p>
                <small>Accuracy: {Math.round(currentAccuracy)}m</small>
              </div>
              <button
                onClick={() => setIsHighRiskArea(false)}
                className={styles.dismissButton}
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
          </div>
        )} */}

        {/* Header */}
        {/* <div className={styles.header}>
          <div className={styles.badge}>
            <i className="fas fa-bolt"></i>
            <span>Real Location Safety Tools</span>
          </div>
          <h2 className={styles.title}>Real-time GPS Safety Features</h2>
          <p className={styles.subtitle}>
            Actual location tracking and emergency resources for {deviceType} devices
          </p>
        </div> */}

        {/* Actions Grid */}
        <div className={styles.grid}>
          {actions.map((action, index) => {
            const badge = getActionBadge(action.type);

            return (
              <div
                key={action.id}
                className={`${styles.card} ${activeAction === action.id ? styles.active : ''} ${isLoading ? styles.loading : ''}`}
                style={{
                  '--action-color': action.color,
                  '--action-gradient': action.gradient,
                  animationDelay: `${index * 100}ms`
                }}
                onClick={() => handleActionClick(action)}
              >
                {isLoading && activeAction === action.id && (
                  <div className={styles.loadingOverlay}>
                    <div className={styles.loadingSpinner}>
                      <i className="fas fa-spinner fa-spin"></i>
                    </div>
                  </div>
                )}

                <div className={styles.background}>
                  <div className={styles.orb}></div>
                  <div className={styles.glow}></div>
                </div>

                <div
                  className={styles.actionBadge}
                  style={{ backgroundColor: badge.color }}
                >
                  {badge.text}
                </div>

                <div className={styles.iconContainer}>
                  <div
                    className={styles.iconWrapper}
                    style={{ background: action.gradient }}
                  >
                    <i className={action.icon}></i>
                  </div>
                </div>

                <div className={styles.content}>
                  <h3 className={styles.label}>{action.label}</h3>
                  <p className={styles.description}>{action.description}</p>

                  {action.id === 'safety-check' && safetyScore && (
                    <div className={styles.safetyInfo}>
                      <span className={styles.safetyScore}>
                        {hasValidSafetyScore ? `${Math.round(safetyScore.score)}% Safe` : 'Loading...'}
                      </span>
                      <span className={styles.safetyLevel}>
                        {hasValidSafetyScore ? normalizedRiskBand(safetyScore.level) : 'Fetching telemetry'}
                      </span>
                      {currentAccuracy && (
                        <span className={styles.accuracyInfo}>
                          {Math.round(currentAccuracy)}m
                        </span>
                      )}
                    </div>
                  )}

                  {action.id === 'live-alerts' && userAlerts.length > 0 && (
                    <div className={styles.alertInfo}>
                      <span className={styles.alertCount}>
                        {userAlerts.length} Latest Alerts
                      </span>
                    </div>
                  )}
                </div>

                <div className={styles.arrow}>
                  <i className="fas fa-chevron-right"></i>
                </div>
              </div>
            );
          })}
        </div>

        {/* Enhanced Status Footer */}
        <div className={styles.footer}>
          <div className={styles.statusGrid}>
            <div className={styles.statusItem}>
              <div className={styles.statusIcon} style={{ background: 'var(--gradient-primary)' }}>
                <i className="fas fa-shield-alt"></i>
              </div>
              <div className={styles.statusContent}>
                <div className={styles.statusLabelRow}>
                  <span className={styles.statusLabel}>Security Posture</span>
                  {dashboardStats?.data_confidence && (
                    <span className={`${styles.confidenceBadge} ${styles[dashboardStats.data_confidence.toLowerCase()]}`}>
                      {dashboardStats.data_confidence.toUpperCase()} DATA
                    </span>
                  )}
                </div>
                <span
                  className={styles.statusValue}
                  style={{
                    color: hasValidSafetyScore
                      ? (safetyScore.score >= 70 ? '#10b981' : safetyScore.score >= 50 ? '#f59e0b' : '#ef4444')
                      : '#94a3b8'
                  }}
                >
                  {hasValidSafetyScore ? `${Math.round(safetyScore.score)}% - ${normalizedRiskBand(safetyScore.level)}` : 'Syncing Telemetry...'}
                </span>
              </div>
            </div>

            <div className={styles.statusItem}>
              <div className={styles.statusIcon} style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
                <i className="fas fa-satellite-dish"></i>
              </div>
              <div className={styles.statusContent}>
                <span className={styles.statusLabel}>Intelligence</span>
                <span className={styles.statusValue}>
                  {userAlerts.length} Alerts Loaded
                </span>
              </div>
            </div>

            <div className={styles.statusItem}>
              <div className={styles.statusIcon} style={{ background: user?.browser_notifications_enabled ? 'linear-gradient(135deg, #10b981, #059669)' : 'linear-gradient(135deg, #6b7280, #4b5563)' }}>
                <i className={`fas ${user?.browser_notifications_enabled ? 'fa-bell' : 'fa-bell-slash'}`}></i>
              </div>
              <div className={styles.statusContent}>
                <span className={styles.statusLabel}>Live Comms</span>
                <span className={styles.statusValue}>
                  {user?.browser_notifications_enabled ? 'Linked' : browserPushSupported ? 'Available' : 'Unsupported'}
                </span>
              </div>
            </div>

            {/* {token && (
              <div className={styles.statusItem}>
                <div className={styles.statusIcon}>
                  <i className={`fas ${locationTrackingEnabled ? 'fa-location-arrow' : 'fa-location-crosshairs'}`}></i>
                </div>
                <div className={styles.statusContent}>
                  <span className={styles.statusLabel}>Live Tracking</span>
                  <span className={styles.statusValue}>
                    {locationTrackingEnabled ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            )} */}

            {/* <div className={styles.statusItem}>
              <div className={styles.statusIcon}>
                <i className={`fas fa-${deviceType}`}></i>
              </div>
              <div className={styles.statusContent}>
                <span className={styles.statusLabel}>Device</span>
                <span className={styles.statusValue}>
                  {deviceType.charAt(0).toUpperCase() + deviceType.slice(1)}
                </span>
              </div>
            </div>
          </div>*/}
        </div>

        {/* Enhanced Current Location Badge */}
        {address && (
          <div className={styles.locationBadge}>
            <div className={styles.locationHeader}>
              <div className={styles.locationIconWrapper}>
                <div className={styles.pulseDot}></div>
                <i className="fas fa-map-marker-alt"></i>
              </div>
              <div className={styles.locationDetails}>
                <span className={styles.locationLabel}>Deployment Region</span>
                <span className={styles.locationAddress}>{address || 'Locating system...'}</span>
              </div>
              <button 
                className={styles.editLocationButton}
                onClick={handleManualLocationInput}
                title="Change location manually"
                disabled={isLoading}
              >
                <i className="fas fa-edit"></i>
              </button>
            </div>
            
            <div className={styles.locationMeta}>
              {isManualLocation && (
                <span className={styles.manualLocationBadge}>
                  <i className="fas fa-hand-pointer"></i>
                  Manual Location
                </span>
              )}
              {currentAccuracy && !isManualLocation && (
                <span className={styles.accuracyBadge}>
                  <i className="fas fa-crosshairs"></i>
                  ±{Math.round(currentAccuracy)}m
                </span>
              )}
              {location && !isManualLocation && (
                <span className={styles.gpsActiveBadge}>
                  <i className="fas fa-satellite"></i>
                  GPS Active
                </span>
              )}
            </div>
          </div>
        )}

          {/* Recent Risk Alerts
          {riskAlerts.length > 0 && (
            <div className={styles.riskAlertsSection}>
              <h4>Recent Real Risk Alerts</h4>
              <div className={styles.riskAlertsList}>
                {riskAlerts.slice(0, 3).map(alert => (
                  <div key={alert.id} className={styles.riskAlertItem}>
                    <i className="fas fa-exclamation-circle"></i>
                    <span>{alert.message}</span>
                    <small>
                      {new Date(alert.timestamp).toLocaleTimeString()} 
                      {alert.accuracy && ` • ${Math.round(alert.accuracy)}m`}
                    </small>
                  </div>
                ))}
              </div>
            </div>
          )} */}
        </div>
      </div>

      {showBrowserPushSettings && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <BrowserPushSettings
              user={user}
              token={token}
              onUpdate={() => window.location.reload()}
              onClose={() => setShowBrowserPushSettings(false)}
            />
          </div>
        </div>
      )}
    </section>
  );
};

export default QuickActions;
