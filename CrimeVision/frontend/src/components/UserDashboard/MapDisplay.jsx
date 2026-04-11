// // MapDisplay.js - Fixed Markers and Start Position
// import React, { useEffect, useState, useRef } from "react";
// import {
//   MapContainer,
//   TileLayer,
//   Marker,
//   Popup,
//   useMap,
//   useMapEvents,
// } from "react-leaflet";
// import L from "leaflet";
// import "leaflet/dist/leaflet.css";
// import "leaflet-polylinedecorator";

// // Fix for default markers in react-leaflet
// delete L.Icon.Default.prototype._getIconUrl;
// L.Icon.Default.mergeOptions({
//   iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
//   iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
//   shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
// });

// // --- Custom Icons ---
// const startIcon = new L.Icon({
//   iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
//   iconSize: [32, 32],
//   className: "pulse-marker"
// });

// const destIcon = new L.Icon({
//   iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
//   iconSize: [32, 32],
//   className: "pulse-marker"
// });

// // Car icon - positioned correctly
// const carIcon = new L.DivIcon({
//   html: `<div style="
//     background: #dc2626; 
//     width: 28px; 
//     height: 28px; 
//     border-radius: 50% 50% 50% 0; 
//     transform: rotate(-45deg); 
//     display: flex; 
//     align-items: center; 
//     justify-content: center;
//     border: 3px solid white;
//     box-shadow: 0 2px 10px rgba(0,0,0,0.3);
//   ">
//     <div style="transform: rotate(45deg); color: white; font-size: 14px;">🚗</div>
//   </div>`,
//   iconSize: [28, 28],
//   iconAnchor: [14, 35],
//   className: 'car-marker-animated'
// });

// // --- Real-time User Position Tracker with Route Recalculation ---
// const UserPositionTracker = ({ 
//   navigationStarted, 
//   onPositionUpdate, 
//   onRouteRecalculation,
//   currentRoute,
//   destination,
//   useManualStart // New prop to control whether to use manual start or current location
// }) => {
//   const map = useMap();
//   const watchId = useRef(null);
//   const lastRecalculation = useRef(null);
//   const positionHistory = useRef([]);

//   // Function to check if user has deviated from route
//   const hasDeviatedFromRoute = (currentPosition, route) => {
//     if (!route?.geometry?.coordinates?.length) return false;
    
//     const userLat = currentPosition[0];
//     const userLng = currentPosition[1];
    
//     let minDistance = Infinity;
    
//     route.geometry.coordinates.forEach(([lng, lat]) => {
//       const distance = Math.sqrt(Math.pow(lat - userLat, 2) + Math.pow(lng - userLng, 2));
//       if (distance < minDistance) {
//         minDistance = distance;
//       }
//     });
    
//     // Consider deviation if more than 100 meters from route
//     const deviationThreshold = 0.001; // ~100 meters
//     return minDistance > deviationThreshold;
//   };

//   // Function to calculate new route from current position
//   const recalculateRoute = async (currentPosition) => {
//     if (!destination || !onRouteRecalculation) return;
    
//     try {
//       console.log("🔄 Recalculating route from current position...");
      
//       const response = await fetch(
//         `https://router.project-osrm.org/route/v1/driving/${
//           currentPosition[1]},${currentPosition[0]
//         };${
//           destination.lng},${destination.lat
//         }?overview=full&geometries=geojson&steps=true`
//       );
      
//       const data = await response.json();
      
//       if (data.routes && data.routes.length > 0) {
//         const newRoute = data.routes[0];
        
//         // Transform to consistent format
//         const transformedRoute = {
//           geometry: newRoute.geometry,
//           distance: (newRoute.distance / 1000).toFixed(2) + ' km',
//           duration: formatDuration(newRoute.duration),
//           steps: newRoute.legs[0].steps.map(step => ({
//             instruction: step.maneuver?.instruction || 'Continue',
//             distance: step.distance > 1000 
//               ? (step.distance / 1000).toFixed(1) + ' km'
//               : step.distance.toFixed(0) + ' m',
//             duration: formatDuration(step.duration)
//           }))
//         };
        
//         onRouteRecalculation(transformedRoute);
//         lastRecalculation.current = Date.now();
        
//         console.log("✅ Route recalculated successfully");
//       }
//     } catch (error) {
//       console.error("❌ Route recalculation failed:", error);
//     }
//   };

//   const formatDuration = (seconds) => {
//     if (seconds < 60) return "<1 min";
//     if (seconds < 3600) return Math.round(seconds / 60) + " min";
//     const hours = Math.floor(seconds / 3600);
//     const minutes = Math.round((seconds % 3600) / 60);
//     return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
//   };

//   useEffect(() => {
//     if (navigationStarted && navigator.geolocation) {
//       console.log("🚗 Starting GPS tracking with route recalculation...");
      
//       watchId.current = navigator.geolocation.watchPosition(
//         (position) => {
//           const { latitude, longitude } = position.coords;
//           const newPosition = [latitude, longitude];
          
//           console.log("📍 New GPS position:", newPosition);
          
//           // Update position - but only if we're not using manual start position
//           if (!useManualStart) {
//             onPositionUpdate(newPosition);
//           }
          
//           // Track position history
//           positionHistory.current.push({
//             position: newPosition,
//             timestamp: Date.now()
//           });
          
//           // Keep only last 10 positions
//           if (positionHistory.current.length > 10) {
//             positionHistory.current.shift();
//           }
          
//           // Check for route deviation and recalculate if needed
//           if (currentRoute && hasDeviatedFromRoute(newPosition, currentRoute)) {
//             const now = Date.now();
//             // Only recalculate every 10 seconds to avoid too many requests
//             if (!lastRecalculation.current || (now - lastRecalculation.current) > 10000) {
//               console.log("🔄 User deviated from route, recalculating...");
//               recalculateRoute(newPosition);
//             }
//           }
          
//           // Smooth map following - always follow user position
//           map.setView(newPosition, map.getZoom(), {
//             animate: true,
//             duration: 1
//           });
//         },
//         (error) => {
//           console.error("Geolocation error:", error);
//         },
//         { 
//           enableHighAccuracy: true,
//           timeout: 5000,
//           maximumAge: 2000 
//         }
//       );
//     } else if (watchId.current) {
//       console.log("🛑 Stopping GPS tracking");
//       navigator.geolocation.clearWatch(watchId.current);
//       watchId.current = null;
//       positionHistory.current = [];
//     }

//     return () => {
//       if (watchId.current) {
//         navigator.geolocation.clearWatch(watchId.current);
//       }
//     };
//   }, [navigationStarted, map, onPositionUpdate, onRouteRecalculation, currentRoute, destination, useManualStart]);

//   return null;
// };

// // --- Fit map to route dynamically ---
// const FitMapToRoute = ({ route }) => {
//   const map = useMap();
//   useEffect(() => {
//     if (route?.geometry?.coordinates?.length) {
//       const latlngs = route.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
//       map.fitBounds(L.latLngBounds(latlngs), { 
//         padding: [60, 60],
//         animate: true,
//         duration: 1
//       });
//     }
//   }, [route, map]);
//   return null;
// };

// // --- Enhanced Route Visualization ---
// const RouteVisualization = ({ route, navigationStarted }) => {
//   const map = useMap();

//   useEffect(() => {
//     if (!route?.geometry?.coordinates?.length) return;

//     // Clear existing route layers
//     map.eachLayer(layer => {
//       if (layer instanceof L.Polyline || layer instanceof L.PolylineDecorator) {
//         map.removeLayer(layer);
//       }
//     });

//     const coordinates = route.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
    
//     // Main route line
//     const mainRoute = L.polyline(coordinates, {
//       color: navigationStarted ? '#10b981' : '#3b82f6',
//       weight: 6,
//       opacity: 0.9,
//       lineCap: 'round',
//       lineJoin: 'round',
//       className: 'animated-route'
//     });

//     // Route glow effect
//     const glowRoute = L.polyline(coordinates, {
//       color: navigationStarted ? '#34d399' : '#60a5fa',
//       weight: 14,
//       opacity: 0.3,
//       lineCap: 'round',
//       lineJoin: 'round',
//       className: 'glow-route'
//     });

//     // Add arrows for direction
//     const decorator = L.polylineDecorator(coordinates, {
//       patterns: [
//         {
//           offset: 10,
//           repeat: 60,
//           symbol: L.Symbol.arrowHead({
//             pixelSize: 12,
//             pathOptions: { 
//               color: navigationStarted ? "#10b981" : "#3b82f6",
//               fillOpacity: 0.8, 
//               weight: 4 
//             },
//           }),
//         },
//       ],
//     });

//     glowRoute.addTo(map);
//     mainRoute.addTo(map);
//     decorator.addTo(map);

//     return () => {
//       map.removeLayer(mainRoute);
//       map.removeLayer(glowRoute);
//       map.removeLayer(decorator);
//     };
//   }, [route, navigationStarted, map]);

//   return null;
// };

// // --- Moving Car Component ---
// const MovingCar = ({ carPosition, navigationStarted, route, useManualStart, manualStartPosition }) => {
//   const map = useMap();
//   const markerRef = useRef(null);

//   // Smooth car movement
//   useEffect(() => {
//     if (carPosition && markerRef.current) {
//       markerRef.current.setLatLng(carPosition);
//     }
//   }, [carPosition]);

//   // Get initial car position
//   const getInitialCarPosition = () => {
//     // If using manual start, use the manually set position
//     if (useManualStart && manualStartPosition) {
//       return [manualStartPosition.lat, manualStartPosition.lng];
//     }
//     // Otherwise use route start
//     if (route?.geometry?.coordinates?.length > 0) {
//       const [startLng, startLat] = route.geometry.coordinates[0];
//       return [startLat, startLng];
//     }
//     return carPosition;
//   };

//   const actualCarPosition = carPosition || getInitialCarPosition();

//   if (!actualCarPosition) {
//     return null;
//   }

//   return (
//     <Marker 
//       position={actualCarPosition} 
//       icon={carIcon}
//       zIndexOffset={1000}
//       ref={markerRef}
//     >
//       <Popup>
//         <div style={{ textAlign: 'center' }}>
//           <strong>🚗 Your Position</strong>
//           <br />
//           Lat: {actualCarPosition[0].toFixed(6)}
//           <br />
//           Lng: {actualCarPosition[1].toFixed(6)}
//           <br />
//           {navigationStarted ? "🟢 Navigation Active" : "🟡 Ready to Start"}
//           <br />
//           {useManualStart ? "📍 Using Manual Start Point" : "📍 Using Current Location"}
//         </div>
//       </Popup>
//     </Marker>
//   );
// };

// // --- Main MapDisplay Component ---
// const MapDisplay = ({
//   route,
//   startPosition,
//   destPosition,
//   onStartSelect,
//   onDestSelect,
//   navigationStarted,
//   carPosition,
//   onCarPositionUpdate,
//   onRouteRecalculation,
//   useManualStart = false // New prop to control start behavior
// }) => {
//   const [startMarker, setStartMarker] = useState(startPosition || null);
//   const [destMarker, setDestMarker] = useState(destPosition || null);
//   const defaultCenter = [31.5204, 74.3587];

//   // Update markers when props change
//   useEffect(() => {
//     if (startPosition) {
//       setStartMarker([startPosition.lat, startPosition.lng]);
//     }
//   }, [startPosition]);

//   useEffect(() => {
//     if (destPosition) {
//       setDestMarker([destPosition.lat, destPosition.lng]);
//     }
//   }, [destPosition]);

//   // Debug props
//   useEffect(() => {
//     console.log("📊 MapDisplay Props:", {
//       navigationStarted,
//       carPosition,
//       hasRoute: !!route,
//       startPosition,
//       destPosition,
//       useManualStart
//     });
//   }, [navigationStarted, carPosition, route, startPosition, destPosition, useManualStart]);

//   // Handle user clicks for placing markers
//   const MapClickHandler = () => {
//     useMapEvents({
//       click(e) {
//         if (navigationStarted) return;
        
//         const { lat, lng } = e.latlng;
//         if (!startMarker) {
//           setStartMarker([lat, lng]);
//           onStartSelect?.({ lat, lng });
//         } else if (!destMarker) {
//           setDestMarker([lat, lng]);
//           onDestSelect?.({ lat, lng });
//         }
//       },
//     });
//     return null;
//   };

//   const mapCenter = startMarker || destMarker || defaultCenter;

//   return (
//     <div className="map-container-wrapper">
//       <MapContainer
//         style={{
//           height: "500px",
//           width: "100%",
//           borderRadius: "20px",
//           boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
//         }}
//         center={mapCenter}
//         zoom={13}
//         scrollWheelZoom
//         zoomControl={true}
//       >
//         <TileLayer
//           attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
//           url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
//         />

//         {route && <FitMapToRoute route={route} />}
//         {route && <RouteVisualization route={route} navigationStarted={navigationStarted} />}
        
//         <UserPositionTracker 
//           navigationStarted={navigationStarted} 
//           onPositionUpdate={onCarPositionUpdate}
//           onRouteRecalculation={onRouteRecalculation}
//           currentRoute={route}
//           destination={destPosition}
//           useManualStart={useManualStart}
//         />
        
//         {/* Moving car marker - Show when route is calculated */}
//         {route && (
//           <MovingCar 
//             carPosition={carPosition} 
//             navigationStarted={navigationStarted}
//             route={route}
//             useManualStart={useManualStart}
//             manualStartPosition={startPosition}
//           />
//         )}

//         {/* Start Marker - ALWAYS visible when set, even during navigation */}
//         {startMarker && Array.isArray(startMarker) && (
//           <Marker
//             position={startMarker}
//             icon={startIcon}
//             draggable={!navigationStarted} // Only draggable when navigation is stopped
//             eventHandlers={{
//               dragend: (e) => {
//                 if (navigationStarted) return;
//                 const pos = e.target.getLatLng();
//                 setStartMarker([pos.lat, pos.lng]);
//                 onStartSelect?.({ lat: pos.lat, lng: pos.lng });
//               },
//             }}
//           >
//             <Popup className="custom-popup">
//               <div className="popup-content">
//                 <strong>🏁 Start Point</strong>
//                 <p>{navigationStarted ? "Navigation in progress" : "Drag to adjust location"}</p>
//                 {useManualStart && <p>📍 Using this as start point</p>}
//               </div>
//             </Popup>
//           </Marker>
//         )}

//         {/* Destination Marker - ALWAYS visible when set */}
//         {destMarker && Array.isArray(destMarker) && (
//           <Marker
//             position={destMarker}
//             icon={destIcon}
//             draggable={!navigationStarted} // Only draggable when navigation is stopped
//             eventHandlers={{
//               dragend: (e) => {
//                 if (navigationStarted) return;
//                 const pos = e.target.getLatLng();
//                 setDestMarker([pos.lat, pos.lng]);
//                 onDestSelect?.({ lat: pos.lat, lng: pos.lng });
//               },
//             }}
//           >
//             <Popup className="custom-popup">
//               <div className="popup-content">
//                 <strong>📍 Destination</strong>
//                 <p>{navigationStarted ? "Navigation in progress" : "Drag to adjust location"}</p>
//               </div>
//             </Popup>
//           </Marker>
//         )}

//         <MapClickHandler />
//       </MapContainer>
//     </div>
//   );
// }

// export default MapDisplay;


// Fixed MapDisplay.js - Route Line & GPS Issues Resolved
import React, { useEffect, useState, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-polylinedecorator";

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// --- Custom Icons ---
const startIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
  iconSize: [32, 32],
  className: "pulse-marker"
});

const destIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
  iconSize: [32, 32],
  className: "pulse-marker"
});

// Car icon - positioned correctly
const carIcon = new L.DivIcon({
  html: `<div style="
    background: #dc2626; 
    width: 28px; 
    height: 28px; 
    border-radius: 50% 50% 50% 0; 
    transform: rotate(-45deg); 
    display: flex; 
    align-items: center; 
    justify-content: center;
    border: 3px solid white;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
  ">
    <div style="transform: rotate(45deg); color: white; font-size: 14px;">🚗</div>
  </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 35],
  className: 'car-marker-animated'
});

// --- Real-time User Position Tracker with Route Recalculation ---
const UserPositionTracker = ({ 
  navigationStarted, 
  onPositionUpdate, 
  onRouteRecalculation,
  currentRoute,
  destination,
  useManualStart
}) => {
  const map = useMap();
  const watchId = useRef(null);
  const lastRecalculation = useRef(null);

  // Function to check if user has deviated from route
  const hasDeviatedFromRoute = (currentPosition, route) => {
    if (!route?.geometry?.coordinates?.length) return false;
    
    const userLat = currentPosition[0];
    const userLng = currentPosition[1];
    
    let minDistance = Infinity;
    
    route.geometry.coordinates.forEach(([lng, lat]) => {
      const distance = Math.sqrt(Math.pow(lat - userLat, 2) + Math.pow(lng - userLng, 2));
      if (distance < minDistance) {
        minDistance = distance;
      }
    });
    
    // Consider deviation if more than 100 meters from route
    const deviationThreshold = 0.001; // ~100 meters
    return minDistance > deviationThreshold;
  };

  // Function to calculate new route from current position
  const recalculateRoute = async (currentPosition) => {
    if (!destination || !onRouteRecalculation) return;
    
    try {
      console.log("🔄 Recalculating route from current position...");
      
      const response = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${
          currentPosition[1]},${currentPosition[0]
        };${
          destination.lng},${destination.lat
        }?overview=full&geometries=geojson&steps=true`
      );
      
      const data = await response.json();
      
      if (data.routes && data.routes.length > 0) {
        const newRoute = data.routes[0];
        
        // Transform to consistent format with improved instruction parsing
        const transformedRoute = {
          geometry: newRoute.geometry,
          distance: (newRoute.distance / 1000).toFixed(2) + ' km',
          duration: formatDuration(newRoute.duration),
          rawDistance: newRoute.distance,
          rawDuration: newRoute.duration,
          steps: newRoute.legs[0].steps.map((step, index) => {
            let instruction = "Continue";

            // First, try to use the OSRM instruction if available
            if (step.maneuver?.instruction) {
              instruction = step.maneuver.instruction
                .replace(/<[^>]*>/g, '') // Remove HTML tags
                .replace(/Destination will be on your|You have arrived at your destination/i, "You will arrive at your destination")
                .trim();
            } else {
              // Fallback: Create instruction based on maneuver type and modifier
              const { type, modifier } = step.maneuver || {};

              if (type === "depart") {
                instruction = "Start navigation";
              } else if (type === "arrive") {
                instruction = "Arrive at destination";
              } else if (type === "turn") {
                const capitalizedModifier = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Turn ${capitalizedModifier}`;
              } else if (type === "new name") {
                instruction = "Continue straight";
              } else if (type === "roundabout") {
                const exit = modifier ? modifier.replace(/^exit_/, '') : "the next";
                instruction = `Enter roundabout and take the ${exit} exit`;
              } else if (type === "merge") {
                const direction = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Merge ${direction}`;
              } else if (type === "on ramp") {
                const direction = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Take ramp ${direction}`;
              } else if (type === "off ramp") {
                const direction = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Take exit ${direction}`;
              } else if (type === "fork") {
                const direction = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Keep ${direction} at fork`;
              } else if (type === "end of road") {
                const direction = modifier ? modifier.charAt(0).toUpperCase() + modifier.slice(1) : "ahead";
                instruction = `Turn ${direction} at end of road`;
              } else if (type === "continue") {
                instruction = "Continue on road";
              } else if (type === "notification") {
                instruction = "Continue";
              } else {
                instruction = "Continue on road";
              }
            }

            return {
              instruction,
              distance: step.distance > 1000
                ? (step.distance / 1000).toFixed(1) + ' km'
                : Math.round(step.distance) + ' m',
              duration: formatDuration(step.duration),
              rawDistance: step.distance,
              rawDuration: step.duration
            };
          })
        };
        
        onRouteRecalculation(transformedRoute);
        lastRecalculation.current = Date.now();
        
        console.log("✅ Route recalculated successfully");
      }
    } catch (error) {
      console.error("❌ Route recalculation failed:", error);
    }
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return "<1 min";
    if (seconds < 3600) return Math.round(seconds / 60) + " min";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  };

  useEffect(() => {
    if (navigationStarted && navigator.geolocation) {
      console.log("🚗 Starting optimized GPS tracking with extended timeout...");

      watchId.current = navigator.geolocation.watchPosition(
        (position) => {
          const { latitude, longitude, accuracy } = position.coords;
          const newPosition = [latitude, longitude];

          if (accuracy < 10) {
            console.log("🟢 HIGH ACCURACY GPS position (accuracy:", accuracy.toFixed(2), "m):", newPosition);
          } else if (accuracy < 50) {
            console.log("🟡 MEDIUM ACCURACY GPS position (accuracy:", accuracy.toFixed(2), "m):", newPosition);
          } else {
            console.log("🟠 LOW ACCURACY GPS position (accuracy:", accuracy.toFixed(2), "m):", newPosition);
          }

          // Update position - but only if we're not using manual start position
          if (!useManualStart) {
            onPositionUpdate(newPosition);
          }

          // Check for route deviation and recalculate if needed
          if (currentRoute && hasDeviatedFromRoute(newPosition, currentRoute)) {
            const now = Date.now();
            // Only recalculate every 10 seconds to avoid too many requests
            if (!lastRecalculation.current || (now - lastRecalculation.current) > 10000) {
              console.log("🔄 User deviated from route, recalculating...");
              recalculateRoute(newPosition);
            }
          }

          // Smooth map following - always follow user position
          map.setView(newPosition, map.getZoom(), {
            animate: true,
            duration: 1
          });
        },
        (error) => {
          console.error("❌ GPS error:", error.code, error.message);
          // Don't crash on GPS errors
        },
        {
          enableHighAccuracy: true,
          timeout: 30000, // Extended timeout for live tracking (30 seconds)
          maximumAge: 3000 // Accept location up to 3 seconds old for smooth updates
        }
      );
    } else if (watchId.current) {
      console.log("🛑 Stopping GPS tracking");
      navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
    }

    return () => {
      if (watchId.current) {
        navigator.geolocation.clearWatch(watchId.current);
      }
    };
  }, [navigationStarted, map, onPositionUpdate, onRouteRecalculation, currentRoute, destination, useManualStart]);

  return null;
};

// --- Fit map to route dynamically ---
const FitMapToRoute = ({ route }) => {
  const map = useMap();
  useEffect(() => {
    if (route?.geometry?.coordinates?.length) {
      // FIXED: Correct coordinate transformation
      const latlngs = route.geometry.coordinates.map((coord) => {
        // OSRM returns [longitude, latitude] but Leaflet needs [latitude, longitude]
        const [lng, lat] = coord;
        return [lat, lng];
      });
      
      const bounds = L.latLngBounds(latlngs);
      
      // Add some padding to ensure route is fully visible
      map.fitBounds(bounds, { 
        padding: [50, 50],
        animate: true,
        duration: 1
      });
    }
  }, [route, map]);
  return null;
};

// --- Enhanced Route Visualization ---
const RouteVisualization = ({ route, navigationStarted, startPosition }) => {
  const map = useMap();
  const routeLayers = useRef([]);

  useEffect(() => {
    if (!route?.geometry?.coordinates?.length) {
      // Clear existing route layers if no route
      routeLayers.current.forEach(layer => {
        if (layer && map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      });
      routeLayers.current = [];
      return;
    }

    // Clear existing route layers
    routeLayers.current.forEach(layer => {
      if (layer && map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });
    routeLayers.current = [];

    // FIXED: Correct coordinate transformation for route display
    const coordinates = route.geometry.coordinates.map(([lng, lat]) => [lat, lng]);

    console.log("🛣️ Drawing route with", coordinates.length, "points");
    console.log("🛣️ Route starts at:", coordinates[0]);
    console.log("🛣️ Route ends at:", coordinates[coordinates.length - 1]);

    // Validate route starts and ends at correct positions
    if (startPosition) {
      const expectedStart = [startPosition.lat, startPosition.lng];
      const actualStart = coordinates[0];
      const distance = Math.sqrt(
        Math.pow(expectedStart[0] - actualStart[0], 2) +
        Math.pow(expectedStart[1] - actualStart[1], 2)
      );
      console.log(`📍 Start position validation: Expected [${expectedStart}], Got [${actualStart}], Distance: ${(distance * 111).toFixed(2)}km`);
    }

    // Main route line
    const mainRoute = L.polyline(coordinates, {
      color: navigationStarted ? '#10b981' : '#3b82f6',
      weight: 6,
      opacity: 0.9,
      lineCap: 'round',
      lineJoin: 'round',
      className: 'animated-route'
    });

    // Route glow effect
    const glowRoute = L.polyline(coordinates, {
      color: navigationStarted ? '#34d399' : '#60a5fa',
      weight: 14,
      opacity: 0.3,
      lineCap: 'round',
      lineJoin: 'round',
      className: 'glow-route'
    });

    // Add arrows for direction
    const decorator = L.polylineDecorator(coordinates, {
      patterns: [
        {
          offset: 10,
          repeat: 60,
          symbol: L.Symbol.arrowHead({
            pixelSize: 12,
            pathOptions: {
              color: navigationStarted ? "#10b981" : "#3b82f6",
              fillOpacity: 0.8,
              weight: 4
            },
          }),
        },
      ],
    });

    // Add all layers to map and track them
    try {
      glowRoute.addTo(map);
      mainRoute.addTo(map);
      decorator.addTo(map);

      routeLayers.current = [glowRoute, mainRoute, decorator];
      console.log("✅ Route visualization layers added successfully");
    } catch (error) {
      console.error("❌ Error adding route layers:", error);
    }

    return () => {
      routeLayers.current.forEach(layer => {
        if (layer && map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      });
      routeLayers.current = [];
    };
  }, [route, navigationStarted, map, startPosition]);

  return null;
};

// --- Moving Car Component ---
const MovingCar = ({ carPosition, navigationStarted, route, useManualStart, manualStartPosition }) => {
  const map = useMap();
  const markerRef = useRef(null);

  // Smooth car movement
  useEffect(() => {
    if (carPosition && markerRef.current) {
      markerRef.current.setLatLng(carPosition);
    }
  }, [carPosition]);

  // Get initial car position
  const getInitialCarPosition = () => {
    // If using manual start, use the manually set position
    if (useManualStart && manualStartPosition) {
      return [manualStartPosition.lat, manualStartPosition.lng];
    }
    // Otherwise use route start
    if (route?.geometry?.coordinates?.length > 0) {
      const [startLng, startLat] = route.geometry.coordinates[0];
      return [startLat, startLng];
    }
    return carPosition;
  };

  const actualCarPosition = carPosition || getInitialCarPosition();

  if (!actualCarPosition) {
    return null;
  }

  return (
    <Marker 
      position={actualCarPosition} 
      icon={carIcon}
      zIndexOffset={1000}
      ref={markerRef}
    >
      <Popup>
        <div style={{ textAlign: 'center' }}>
          <strong>🚗 Your Position</strong>
          <br />
          Lat: {actualCarPosition[0].toFixed(6)}
          <br />
          Lng: {actualCarPosition[1].toFixed(6)}
          <br />
          {navigationStarted ? "🟢 Navigation Active" : "🟡 Ready to Start"}
          <br />
          {useManualStart ? "📍 Using Manual Start Point" : "📍 Using Current Location"}
        </div>
      </Popup>
    </Marker>
  );
};

// --- Main MapDisplay Component ---
const MapDisplay = ({
  route,
  startPosition,
  destPosition,
  onStartSelect,
  onDestSelect,
  navigationStarted,
  carPosition,
  onCarPositionUpdate,
  onRouteRecalculation,
  useManualStart = false,
  onStartDragEnd,
  onDestDragEnd
}) => {
  const [startMarker, setStartMarker] = useState(startPosition || null);
  const [destMarker, setDestMarker] = useState(destPosition || null);
  const defaultCenter = [31.5204, 74.3587];

  // Update markers when props change
  useEffect(() => {
    if (startPosition) {
      setStartMarker([startPosition.lat, startPosition.lng]);
    }
  }, [startPosition]);

  useEffect(() => {
    if (destPosition) {
      setDestMarker([destPosition.lat, destPosition.lng]);
    }
  }, [destPosition]);

  // Debug props
  useEffect(() => {
    console.log("📊 MapDisplay Props:", {
      navigationStarted,
      carPosition,
      hasRoute: !!route,
      startPosition,
      destPosition,
      useManualStart
    });
  }, [navigationStarted, carPosition, route, startPosition, destPosition, useManualStart]);

  // Handle user clicks for placing markers
  const MapClickHandler = () => {
    useMapEvents({
      click(e) {
        if (navigationStarted) return;
        
        const { lat, lng } = e.latlng;
        if (!startMarker) {
          setStartMarker([lat, lng]);
          onStartSelect?.({ lat, lng });
        } else if (!destMarker) {
          setDestMarker([lat, lng]);
          onDestSelect?.({ lat, lng });
        }
      },
    });
    return null;
  };

  const mapCenter = startMarker || destMarker || defaultCenter;

  return (
    <div className="map-container-wrapper">
      <MapContainer
        style={{
          height: "500px",
          width: "100%",
          borderRadius: "20px",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
        center={mapCenter}
        zoom={13}
        scrollWheelZoom
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {route && <FitMapToRoute route={route} />}
        {route && <RouteVisualization route={route} navigationStarted={navigationStarted} startPosition={startPosition} />}
        
        <UserPositionTracker 
          navigationStarted={navigationStarted} 
          onPositionUpdate={onCarPositionUpdate}
          onRouteRecalculation={onRouteRecalculation}
          currentRoute={route}
          destination={destPosition}
          useManualStart={useManualStart}
        />
        
        {/* Moving car marker - Show when route is calculated */}
        {route && (
          <MovingCar 
            carPosition={carPosition} 
            navigationStarted={navigationStarted}
            route={route}
            useManualStart={useManualStart}
            manualStartPosition={startPosition}
          />
        )}

        {/* Start Marker - ALWAYS visible when set, even during navigation */}
        {startMarker && Array.isArray(startMarker) && (
          <Marker
            position={startMarker}
            icon={startIcon}
            draggable={!navigationStarted}
            eventHandlers={{
              dragend: (e) => {
                if (navigationStarted) return;
                const pos = e.target.getLatLng();
                setStartMarker([pos.lat, pos.lng]);
                onStartSelect?.({ lat: pos.lat, lng: pos.lng });
              },
            }}
          >
            <Popup className="custom-popup">
              <div className="popup-content">
                <strong>🏁 Start Point</strong>
                <p>{navigationStarted ? "Navigation in progress" : "Drag to adjust location"}</p>
                {useManualStart && <p>📍 Using this as start point</p>}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker - ALWAYS visible when set */}
        {destMarker && Array.isArray(destMarker) && (
          <Marker
            position={destMarker}
            icon={destIcon}
            draggable={!navigationStarted}
            eventHandlers={{
              dragend: (e) => {
                if (navigationStarted) return;
                const pos = e.target.getLatLng();
                setDestMarker([pos.lat, pos.lng]);
                onDestSelect?.({ lat: pos.lat, lng: pos.lng });
              },
            }}
          >
            <Popup className="custom-popup">
              <div className="popup-content">
                <strong>📍 Destination</strong>
                <p>{navigationStarted ? "Navigation in progress" : "Drag to adjust location"}</p>
              </div>
            </Popup>
          </Marker>
        )}

        <MapClickHandler />
      </MapContainer>
    </div>
  );
}

export default MapDisplay;
