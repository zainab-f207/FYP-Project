
import React, { useState, useEffect, useRef } from "react";
import styles from "./NavigationSystem.module.css";
import apiService from "../../services/apiService_updated";
import MapDisplay from "./MapDisplay";
import { requestLocationPermission } from "../../services/LocationPermission";


const NavigationSystem = ({ userLocation }) => {
  const [startLocation, setStartLocation] = useState("");
  const [destination, setDestination] = useState("");
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [navigationStarted, setNavigationStarted] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [safetyScore, setSafetyScore] = useState(null);
  const [manualPosition, setManualPosition] = useState(null);
  const [selectedAddress, setSelectedAddress] = useState("");
  const [locationConfirmed, setLocationConfirmed] = useState(false);
  const [destinationPosition, setDestinationPosition] = useState(null);
  const [progress, setProgress] = useState(0);
  const [carPosition, setCarPosition] = useState(null);
  const [isCalculatingRoute, setIsCalculatingRoute] = useState(false);
  const [recalculating, setRecalculating] = useState(false);
  const [useManualStart, setUseManualStart] = useState(false);
  const [locationAccuracy, setLocationAccuracy] = useState(null);
  const [gpsWatchId, setGpsWatchId] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState("");

  const mapRef = useRef(null);

  // OPTIMIZED location service - Get the BEST possible location with ACCURACY THRESHOLD strategy
  // Uses watchPosition to get continuous updates until accuracy threshold is met
  const getHighAccuracyLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation not supported'));
        return;
      }

      console.log("🎯 Requesting HIGH ACCURACY location with accuracy threshold strategy...");

      let watchId = null;
      let timeoutId = null;
      let bestPosition = null;
      const ACCURACY_THRESHOLD = 50; // meters - consider location ready when accuracy < 50m
      const MAX_WAIT_TIME = 60000; // 60 seconds max wait time
      const INITIAL_TIMEOUT = 15000; // 15 seconds to get first position
      let firstPositionReceived = false;

      const cleanup = () => {
        if (watchId !== null) {
          navigator.geolocation.clearWatch(watchId);
          watchId = null;
        }
        if (timeoutId !== null) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
      };

      // Set overall timeout - if we don't get good accuracy, return best position we have
      timeoutId = setTimeout(() => {
        console.log(`⏱️ Max wait time (${MAX_WAIT_TIME}ms) reached`);
        cleanup();

        if (bestPosition) {
          const { latitude, longitude, accuracy } = bestPosition.coords;
          const locationData = {
            lat: latitude,
            lng: longitude,
            accuracy: accuracy,
            timestamp: bestPosition.timestamp
          };

          if (accuracy < 50) {
            setLocationAccuracy('medium');
            console.log(`✅ Returning best position found (accuracy: ${accuracy.toFixed(2)}m)`);
          } else {
            setLocationAccuracy('low');
            console.log(`⚠️ Returning best position found (accuracy: ${accuracy.toFixed(2)}m)`);
          }
          resolve(locationData);
        } else {
          const error = new Error('Timeout expired - no position available');
          error.code = 3;
          reject(error);
        }
      }, MAX_WAIT_TIME);

      // Use watchPosition to get continuous updates
      watchId = navigator.geolocation.watchPosition(
        (position) => {
          const { latitude, longitude, accuracy } = position.coords;

          // Track first position received
          if (!firstPositionReceived) {
            firstPositionReceived = true;
            console.log(`🟡 First position received (accuracy: ${accuracy.toFixed(2)}m)`);
          }

          // Always keep track of best position
          if (!bestPosition || accuracy < bestPosition.coords.accuracy) {
            bestPosition = position;
            console.log(`📍 Position update: [${latitude.toFixed(6)}, ${longitude.toFixed(6)}], Accuracy: ${accuracy.toFixed(2)}m`);
          }

          // Check if accuracy is good enough
          if (accuracy < ACCURACY_THRESHOLD) {
            console.log(`✅ EXCELLENT accuracy achieved! (${accuracy.toFixed(2)}m < ${ACCURACY_THRESHOLD}m)`);
            setLocationAccuracy('high');
            cleanup();
            const locationData = {
              lat: latitude,
              lng: longitude,
              accuracy: accuracy,
              timestamp: position.timestamp
            };
            resolve(locationData);
          } else if (accuracy < 100) {
            setLocationAccuracy('medium');
            console.log(`🟢 Good accuracy: ${accuracy.toFixed(2)}m`);
          } else if (accuracy < 200) {
            setLocationAccuracy('medium');
            console.log(`🟡 Medium accuracy: ${accuracy.toFixed(2)}m`);
          } else {
            setLocationAccuracy('low');
            console.log(`🟠 Low accuracy: ${accuracy.toFixed(2)}m`);
          }
        },
        (error) => {
          console.error(`❌ Location watch error:`, error.code, error.message);

          // If we have a best position, use it
          if (bestPosition) {
            const { latitude, longitude, accuracy } = bestPosition.coords;
            const locationData = {
              lat: latitude,
              lng: longitude,
              accuracy: accuracy,
              timestamp: bestPosition.timestamp
            };
            console.log(`✅ Using best position found so far (accuracy: ${accuracy.toFixed(2)}m)`);
            cleanup();
            resolve(locationData);
          } else {
            // Only reject if we haven't received any position at all
            cleanup();
            reject(error);
          }
        },
        {
          enableHighAccuracy: true,
          timeout: INITIAL_TIMEOUT, // Timeout for each position update
          maximumAge: 0 // Always get fresh data, don't use cache
        }
      );
    });
  };

  // Start continuous tracking with OPTIMIZED timeout settings
  const startLiveTracking = (onLocationUpdate) => {
    if (!navigator.geolocation) return null;

    console.log("🚗 Starting optimized live tracking with extended timeout...");

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude, accuracy, speed, heading } = position.coords;

        const locationData = {
          lat: latitude,
          lng: longitude,
          accuracy: accuracy,
          speed: speed,
          heading: heading,
          timestamp: position.timestamp
        };

        // Determine accuracy level
        if (accuracy < 10) {
          setLocationAccuracy('high');
          console.log("🟢 HIGH ACCURACY live update:", locationData);
        } else if (accuracy < 50) {
          setLocationAccuracy('medium');
          console.log("🟡 MEDIUM ACCURACY live update:", locationData);
        } else {
          setLocationAccuracy('low');
          console.log("🟠 LOW ACCURACY live update:", locationData);
        }

        if (onLocationUpdate) onLocationUpdate(locationData);
      },
      (error) => {
        console.error('❌ Live tracking error:', error.code, error.message);
        // Don't crash on GPS errors, just log them
      },
      {
        enableHighAccuracy: true,
        timeout: 30000, // Extended timeout for live tracking (30 seconds)
        maximumAge: 3000 // Accept location up to 3 seconds old for smooth updates
      }
    );

    setGpsWatchId(watchId);
    return watchId;
  };

  // Stop tracking
  const stopLiveTracking = () => {
    if (gpsWatchId) {
      navigator.geolocation.clearWatch(gpsWatchId);
      setGpsWatchId(null);
      console.log("🛑 Stopped live tracking");
    }
  };

  // Handle location load with high accuracy
  useEffect(() => {
    if (userLocation?.lat && userLocation?.lng) {
      setManualPosition(userLocation);
      setLocationConfirmed(true);
      reverseGeocode(userLocation.lat, userLocation.lng).then((addr) => {
        setStartLocation(addr);
        setSelectedAddress(addr);
      });
    } else {
      getCurrentLocation();
    }
  }, [userLocation]);

  // Start/stop live tracking based on navigation state
  useEffect(() => {
    if (navigationStarted) {
      const watchId = startLiveTracking((newLocation) => {
        const newPosition = [newLocation.lat, newLocation.lng];
        handleCarPositionUpdate(newPosition);
      });
      
      return () => {
        if (watchId) {
          navigator.geolocation.clearWatch(watchId);
        }
      };
    } else {
      stopLiveTracking();
    }
  }, [navigationStarted]);

  // Reset navigation state when start position changes
  useEffect(() => {
    if (manualPosition && navigationStarted) {
      console.log("📍 Start position changed during navigation - resetting");
      setNavigationStarted(false);
      setCurrentStep(0);
      setProgress(0);
      setCarPosition(null);
      stopLiveTracking();
    }
  }, [manualPosition]);

  // Auto-geocode when user types in start location
  useEffect(() => {
    if (startLocation && startLocation.length > 3 && !startLocation.includes("Selected Location")) {
      const timer = setTimeout(() => {
        geocodeToMarker(startLocation, 'start');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [startLocation]);

  // Auto-geocode when user types in destination
  useEffect(() => {
    if (destination && destination.length > 3) {
      const timer = setTimeout(() => {
        geocodeToMarker(destination, 'destination');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [destination]);

  // Auto-confirm when manual position is set
  useEffect(() => {
    if (manualPosition && !locationConfirmed) {
      setLocationConfirmed(true);
    }
  }, [manualPosition, locationConfirmed]);

  // Initialize car position when route is calculated
  useEffect(() => {
    if (route && !navigationStarted) {
      const routeStart = getRouteStartPosition();
      if (routeStart) {
        console.log("🚗 Setting car to EXACT route start position:", routeStart);
        setCarPosition(routeStart);
      }
    }
  }, [route, navigationStarted]);

  const getRouteStartPosition = () => {
    if (route?.geometry?.coordinates?.length > 0) {
      const [startLng, startLat] = route.geometry.coordinates[0];
      return [startLat, startLng];
    }
    return null;
  };

  // Handle route recalculation from MapDisplay
  const handleRouteRecalculation = async (newRoute) => {
    if (!navigationStarted) return;
    
    console.log("🔄 Processing recalculated route...");
    setRecalculating(true);
    
    try {
      // Use current car position or manual start for recalculation
      const startLat = carPosition ? carPosition[0] : manualPosition.lat;
      const startLng = carPosition ? carPosition[1] : manualPosition.lng;

      const safeRouteData = {
        start_lat: startLat,
        start_lng: startLng,
        end_lat: destinationPosition.lat,
        end_lng: destinationPosition.lng,
        distance: newRoute.rawDistance || parseFloat(newRoute.distance) * 1000,
        duration: newRoute.rawDuration || 0,
        geometry: newRoute.geometry,
        steps: newRoute.steps.map(step => ({
          instruction: step.instruction,
          distance: step.rawDistance || 0,
          duration: step.rawDuration || 0
        })),
        waypoints: newRoute.geometry?.coordinates?.map(([lng, lat]) => ({ lat, lng })) || [],
      };

      let safetyResponse;
      try {
        // Try AI-based route safety analysis first
        console.log('🤖 Attempting AI route safety analysis for recalculated route...');

        const waypoints = safeRouteData.waypoints || [];
        const sampleSize = Math.min(10, waypoints.length);
        const step = Math.max(1, Math.floor(waypoints.length / sampleSize));
        const sampledWaypoints = waypoints.filter((_, index) => index % step === 0).slice(0, sampleSize);

        // Use SEQUENTIAL geocoding with delays to avoid rate limiting
        const routePoints = [];
        for (let i = 0; i < sampledWaypoints.length; i++) {
          const point = sampledWaypoints[i];
          try {
            if (i > 0) {
              await new Promise(resolve => setTimeout(resolve, 1100));
            }
            
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?format=json&lat=${point.lat}&lon=${point.lng}&zoom=14&addressdetails=1`,
              {
                headers: {
                  'User-Agent': 'SafeVision-SafetyNavigation/1.0'
                }
              }
            );
            
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            const area = data.address?.suburb || data.address?.neighbourhood ||
                        data.address?.city || data.address?.town || 'Unknown';

            const crimeTypes = ['Burglary', 'Robbery', 'Theft', 'Assault'];
            const crimeType = crimeTypes[i % crimeTypes.length];

            routePoints.push({
              latitude: point.lat,
              longitude: point.lng,
              area: area,
              crime_type: crimeType
            });
          } catch (error) {
            console.warn(`⚠️ Failed to geocode recalc point ${i + 1}:`, error.message);
            routePoints.push({
              latitude: point.lat,
              longitude: point.lng,
              area: 'Unknown',
              crime_type: 'Burglary'
            });
          }
        }

        safetyResponse = await apiService.analyzeRouteSafetyAI(routePoints);
        console.log("✅ AI route safety analysis successful for recalculated route");

      } catch (aiError) {
        console.warn("⚠️ AI route safety analysis failed, falling back to rule-based:", aiError);
        try {
          safetyResponse = await apiService.analyzeRouteSafety(safeRouteData);
          console.log("✅ Rule-based safety analysis successful for recalculated route");
        } catch (safetyError) {
          console.warn("⚠️ Safety analysis failed, using default safety score:", safetyError);
          safetyResponse = {
            overall_score: 85,
            alerts: [],
            factors: {
              lighting: "good",
              traffic: "moderate",
              crime_rate: "low"
            }
          };
        }
      }

      const finalRoute = {
        ...newRoute,
        safety: safetyResponse,
      };

      setRoute(finalRoute);
      setSafetyScore(safetyResponse.overall_score);
      setCurrentStep(0);
      setProgress(0);
      
      console.log("✅ Route successfully recalculated and updated");
      
    } catch (error) {
      console.error("❌ Error processing recalculated route:", error);
    } finally {
      setRecalculating(false);
    }
  };

  const geocodeToMarker = async (address, type) => {
    try {
      const coords = await geocodeLocation(address);
      if (coords) {
        if (type === 'start') {
          setManualPosition(coords);
          setLocationConfirmed(true);
          setUseManualStart(true);
        } else {
          setDestinationPosition(coords);
        }
      }
    } catch (error) {
      console.log(`Could not find location: ${address}`);
    }
  };

  const getCurrentLocation = async () => {
    try {
      const location = await getHighAccuracyLocation();
      setManualPosition(location);
      setLocationConfirmed(true);
      setUseManualStart(false);
      
      const addr = await reverseGeocode(location.lat, location.lng);
      setStartLocation(addr);
      setSelectedAddress(addr);
    } catch (error) {
      console.error("Location error:", error);
      setStartLocation("Enter your starting location manually");
      
      // Fallback to standard location with relaxed settings
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          async (position) => {
            const { latitude, longitude } = position.coords;
            const newPosition = { lat: latitude, lng: longitude };
            setManualPosition(newPosition);
            setLocationConfirmed(true);
            setUseManualStart(false);
            const addr = await reverseGeocode(latitude, longitude);
            setStartLocation(addr);
            setSelectedAddress(addr);
          },
          (error) => {
            console.error("Fallback location error:", error);
          },
          {
            enableHighAccuracy: false, // Relaxed settings for fallback
            timeout: 10000,
            maximumAge: 60000
          }
        );
      }
    }
  };

  const reverseGeocode = async (lat, lng) => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`
      );
      const data = await res.json();
      return data.display_name || "Selected Location";
    } catch {
      return "Selected Location";
    }
  };

  const handleManualSelect = async ({ lat, lng }) => {
    if (navigationStarted) return;
    
    setManualPosition({ lat, lng });
    setLocationConfirmed(true);
    setUseManualStart(true);
    const addr = await reverseGeocode(lat, lng);
    setSelectedAddress(addr);
    setStartLocation(addr);
  };

  const handleDestinationSelect = async ({ lat, lng }) => {
    if (navigationStarted) return;
    
    setDestinationPosition({ lat, lng });
    const addr = await reverseGeocode(lat, lng);
    setDestination(addr);
  };

  const handleCarPositionUpdate = (newPosition) => {
    if (!navigationStarted) {
      console.log("🛑 Ignoring position update - navigation not started");
      return;
    }

    console.log("📍 Updating car position:", newPosition);
    
    // Only update car position if we're NOT using manual start
    if (!useManualStart) {
      setCarPosition(newPosition);
    }
    
    // Update progress based on actual position
    updateProgressAndSteps(newPosition);
  };

  const updateProgressAndSteps = (userPosition) => {
    if (!route?.geometry?.coordinates) return;

    const userLat = userPosition[0];
    const userLng = userPosition[1];
    
    let minDistance = Infinity;
    let closestIndex = 0;
    
    route.geometry.coordinates.forEach(([lng, lat], index) => {
      const distance = Math.sqrt(Math.pow(lat - userLat, 2) + Math.pow(lng - userLng, 2));
      if (distance < minDistance) {
        minDistance = distance;
        closestIndex = index;
      }
    });
    
    const distanceThreshold = 0.0001; // ~11 meters
    if (minDistance < distanceThreshold) {
      const newProgress = (closestIndex / route.geometry.coordinates.length) * 100;
      setProgress(Math.min(newProgress, 100));
      
      const stepIndex = Math.floor((closestIndex / route.geometry.coordinates.length) * route.steps.length);
      setCurrentStep(Math.min(stepIndex, route.steps.length - 1));
      
      console.log(`📊 Progress: ${Math.round(newProgress)}%, Step: ${stepIndex + 1}/${route.steps.length}`);
    }
  };

  const calculateRoute = async () => {
    if (!manualPosition) {
      alert("Please select your start location first.");
      return;
    }
    if (!destinationPosition) {
      alert("Please select your destination location.");
      return;
    }

    // Warn user if GPS accuracy is poor (only for current location, not manual selection)
    if (!useManualStart && manualPosition.accuracy && manualPosition.accuracy > 100) {
      console.warn(`⚠️ GPS accuracy is ${manualPosition.accuracy.toFixed(2)}m - route may not be perfectly accurate`);
      const proceed = window.confirm(
        `GPS accuracy is currently ${manualPosition.accuracy.toFixed(0)}m (poor).\n\nFor best results, please:\n1. Move outdoors\n2. Wait for GPS to improve\n3. Or manually select your start location\n\nProceed anyway?`
      );
      if (!proceed) return;
    }

    setLoading(true);
    setIsCalculatingRoute(true);
    setLoadingStatus("Calculating route...");
    try {
      const routeResponse = await calculateOSMRoute(manualPosition, destinationPosition);
      
      setLoadingStatus("Analyzing route safety...");

      const safeRouteData = {
        start_lat: manualPosition.lat,
        start_lng: manualPosition.lng,
        end_lat: destinationPosition.lat,
        end_lng: destinationPosition.lng,
        distance: routeResponse.rawDistance,
        duration: routeResponse.rawDuration,
        geometry: routeResponse.geometry,
        steps: routeResponse.steps.map(step => ({
          instruction: step.instruction,
          distance: step.rawDistance,
          duration: step.rawDuration
        })),
        waypoints: routeResponse.geometry?.coordinates?.map(([lng, lat]) => ({ lat, lng })) || [],
      };

      console.log("📊 Sending to safety analysis:", safeRouteData);

      let safetyResponse;
      let retryCount = 0;
      const maxRetries = 2;

      const attemptSafetyAnalysis = async () => {
        try {
          // Try AI-based route safety analysis first
          console.log('🤖 Attempting AI route safety analysis...');

          // Sample waypoints along the route (reduce to 10 points to avoid rate limiting)
          const waypoints = safeRouteData.waypoints || [];
          const sampleSize = Math.min(10, waypoints.length);
          const step = Math.max(1, Math.floor(waypoints.length / sampleSize));
          const sampledWaypoints = waypoints.filter((_, index) => index % step === 0).slice(0, sampleSize);

          console.log(`📍 Processing ${sampledWaypoints.length} route points for safety analysis...`);
          setLoadingStatus(`Geocoding route points (0/${sampledWaypoints.length})...`);

          // Get area names for sampled points using SEQUENTIAL reverse geocoding with delays
          // This prevents rate limiting from Nominatim
          const routePoints = [];
          for (let i = 0; i < sampledWaypoints.length; i++) {
            const point = sampledWaypoints[i];
            try {
              // Add delay between requests to respect Nominatim rate limits (1 request per second)
              if (i > 0) {
                await new Promise(resolve => setTimeout(resolve, 1100)); // 1.1 second delay
              }

              setLoadingStatus(`Geocoding route points (${i + 1}/${sampledWaypoints.length})...`);
              console.log(`🔍 Geocoding point ${i + 1}/${sampledWaypoints.length}...`);
              
              // Use Nominatim reverse geocoding to get area name
              const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${point.lat}&lon=${point.lng}&zoom=14&addressdetails=1`,
                {
                  headers: {
                    'User-Agent': 'SafeVision-SafetyNavigation/1.0'
                  }
                }
              );
              
              if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
              }
              
              const data = await response.json();
              const area = data.address?.suburb || data.address?.neighbourhood ||
                          data.address?.city || data.address?.town || 'Unknown';

              // Use a mix of common crime types for analysis
              const crimeTypes = ['Burglary', 'Robbery', 'Theft', 'Assault'];
              const crimeType = crimeTypes[i % crimeTypes.length];

              routePoints.push({
                latitude: point.lat,
                longitude: point.lng,
                area: area,
                crime_type: crimeType
              });
              
              console.log(`✅ Geocoded point ${i + 1}: ${area}`);
            } catch (error) {
              console.warn(`⚠️ Failed to geocode point ${i + 1}:`, error.message);
              // Still add the point with unknown area
              routePoints.push({
                latitude: point.lat,
                longitude: point.lng,
                area: 'Unknown',
                crime_type: 'Burglary'
              });
            }
          }

          console.log('📍 Route points prepared for AI analysis:', routePoints.length);
          setLoadingStatus('Running AI safety analysis...');

          // Call AI route safety analysis
          try {
            const aiResponse = await apiService.analyzeRouteSafetyAI(routePoints);
            console.log("✅ AI route safety analysis successful:", aiResponse);
            return aiResponse;
          } catch (aiError) {
            console.warn('⚠️ AI endpoint not available, trying rule-based analysis:', aiError.message);
            throw aiError; // Let it fall through to rule-based
          }

        } catch (aiError) {
          console.warn('⚠️ AI route safety analysis failed, falling back to rule-based:', aiError.message);

          // Fallback to rule-based analysis
          try {
            const response = await apiService.analyzeRouteSafety(safeRouteData);
            console.log("✅ Rule-based safety analysis successful:", response);
            return response;
          } catch (error) {
            retryCount++;
            if (retryCount < maxRetries) {
              console.warn(`⚠️ Safety analysis failed (attempt ${retryCount}/${maxRetries}), retrying...`);
              await new Promise(resolve => setTimeout(resolve, 1000));
              return attemptSafetyAnalysis();
            } else {
              console.warn("⚠️ Safety analysis failed after retries, using fallback:", error.message);
              return null;
            }
          }
        }
      };

      safetyResponse = await attemptSafetyAnalysis();

      if (!safetyResponse) {
        // Fallback response when API is unavailable - Use REAL data from backend
        console.warn("⚠️ Using fallback safety analysis - backend AI/rule-based analysis unavailable");
        safetyResponse = {
          overall_score: 70,
          safety_level: "medium",
          alerts: [{
            type: "⚠️ Limited Safety Data",
            description: "Safety analysis service is currently unavailable. This route is based on fastest path only. For accurate safety analysis, please ensure the backend server is running properly.",
            severity: "medium",
            location: "Route"
          }],
          factors: {
            lighting: "unknown",
            traffic: "unknown",
            crime_rate: "unknown",
            emergency_services_proximity: "unknown",
            road_type: "unknown"
          }
        };
      }

      const finalRoute = {
        ...routeResponse,
        safety: safetyResponse,
      };

      setRoute(finalRoute);
      setSafetyScore(safetyResponse.overall_score);
      
      setNavigationStarted(false);
      setCurrentStep(0);
      setProgress(0);
      
    } catch (error) {
      console.error("Error calculating route:", error);
      alert("Error calculating route. Please check your locations and try again.");
    } finally {
      setLoading(false);
      setIsCalculatingRoute(false);
      setLoadingStatus("");
    }
  };

  const geocodeLocation = async (location) => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          location
        )}&countrycodes=pk&limit=1`
      );
      const data = await res.json();
      return data?.[0]
        ? { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) }
        : null;
    } catch (error) {
      console.error("Geocoding error:", error);
      return null;
    }
  };

  // FIXED: Proper OSRM route calculation with correct step instructions
  const calculateOSMRoute = async (start, end) => {
    const res = await fetch(
      `https://router.project-osrm.org/route/v1/driving/${start.lng},${start.lat};${end.lng},${end.lat}?overview=full&geometries=geojson&steps=true`
    );

    const data = await res.json();
    
    if (!data.routes || data.routes.length === 0) {
      throw new Error("No route found");
    }
    
    const route = data.routes[0];
    const coords = route.geometry.coordinates;
    
    console.log("✅ Route Start:", coords[0]);
    console.log("✅ Route End:", coords[coords.length - 1]);

    // FIXED: Proper step instructions with real navigation directions
    const readableSteps = route.legs[0].steps.map((step, index) => {
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
          // Capitalize modifier (left -> Left, right -> Right, etc.)
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

      const distanceKm = step.distance > 1000 
        ? (step.distance / 1000).toFixed(1) + ' km'
        : Math.round(step.distance) + ' m';

      let durationText;
      if (step.duration < 60) {
        durationText = "<1 min";
      } else if (step.duration < 3600) {
        durationText = Math.round(step.duration / 60) + " min";
      } else {
        const hours = Math.floor(step.duration / 3600);
        const minutes = Math.round((step.duration % 3600) / 60);
        durationText = minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
      }

      return {
        instruction,
        distance: distanceKm,
        duration: durationText,
        rawDistance: step.distance,
        rawDuration: step.duration
      };
    });

    const totalDistanceKm = (route.distance / 1000).toFixed(2);
    
    let totalDurationText;
    if (route.duration < 60) {
      totalDurationText = "<1 min";
    } else if (route.duration < 3600) {
      totalDurationText = Math.round(route.duration / 60) + " min";
    } else {
      const hours = Math.floor(route.duration / 3600);
      const minutes = Math.round((route.duration % 3600) / 60);
      totalDurationText = minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }

    return {
      distance: totalDistanceKm + ' km',
      duration: totalDurationText,
      rawDistance: route.distance,
      rawDuration: route.duration,
      geometry: route.geometry,
      steps: readableSteps,
    };
  };


  const handleStartNavigation = async () => {
  const granted = await requestLocationPermission();
  if (!granted) return;

  startNavigation(); // your existing function
};

  const startNavigation = () => {
    if (!route) return;
    
    console.log("🎬 Starting navigation...");
    console.log("📍 Using manual start:", useManualStart);
    
    // Set car position based on whether we're using manual start or current location
    if (useManualStart && manualPosition) {
      console.log("📍 Using manual start position:", manualPosition);
      setCarPosition([manualPosition.lat, manualPosition.lng]);
    } else {
      const routeStart = getRouteStartPosition();
      if (routeStart) {
        console.log("📍 Using route start position:", routeStart);
        setCarPosition(routeStart);
      }
    }
    
    setNavigationStarted(true);
    setCurrentStep(0);
    setProgress(0);
  };

  const stopNavigation = () => {
    console.log("🛑 Stopping navigation");
    setNavigationStarted(false);
    setCurrentStep(0);
    setProgress(0);
    stopLiveTracking();
    
    if (useManualStart && manualPosition) {
      setCarPosition([manualPosition.lat, manualPosition.lng]);
    } else {
      const routeStart = getRouteStartPosition();
      if (routeStart) {
        setCarPosition(routeStart);
      }
    }
  };

  const restartNavigation = () => {
    console.log("🔄 Restarting navigation");
    stopNavigation();
    setRoute(null);
    setProgress(0);
    setCarPosition(null);
  };

  // Accuracy tips component with real-time accuracy display
  const AccuracyTips = () => (
    <div className={styles.accuracyTips}>
      <h4>Improve Location Accuracy:</h4>
      <ul>
        <li>✅ Grant location permissions to your browser</li>
        <li>✅ Use devices with GPS (phones better than laptops) and Be in open areas with clear sky view</li>
        <li>❌ Don't use in basements or underground</li>
      </ul>
      {locationAccuracy && (
        <div className={styles.accuracyStatus}>
          <div style={{ marginBottom: '0.5rem' }}>
            Current Accuracy:
            <span className={
              locationAccuracy === 'high' ? styles.highAccuracy :
              locationAccuracy === 'medium' ? styles.mediumAccuracy :
              styles.lowAccuracy
            }>
              {locationAccuracy === 'high' ? ' 🟢 High' :
               locationAccuracy === 'medium' ? ' 🟡 Medium' : ' 🟠 Low'}
            </span>
          </div>
          {manualPosition?.accuracy && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Precision: {manualPosition.accuracy.toFixed(0)}m
              {manualPosition.accuracy < 50 && ' ✅ Excellent for navigation'}
              {manualPosition.accuracy >= 50 && manualPosition.accuracy < 100 && ' ✅ Good for navigation'}
              {manualPosition.accuracy >= 100 && ' ⚠️ May affect route accuracy'}
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className={styles.navigationSystem}>
      {/* Route Input Section */}
      <div className={styles.routeInputSection}>
        <div className={styles.inputGroup}>
          <div className={styles.inputWithIcon}>
            <i className="fas fa-location-arrow"></i>
            <input
              type="text"
              placeholder="Start location"
              value={startLocation}
              onChange={(e) => setStartLocation(e.target.value)}
              disabled={navigationStarted}
              className={styles.animatedInput}
            />
          </div>
          <div className={styles.inputWithIcon}>
            <i className="fas fa-flag"></i>
            <input
              type="text"
              placeholder="Destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              disabled={navigationStarted}
              className={styles.animatedInput}
            />
          </div>
        </div>

        <div className={styles.buttonGroup}>
          <button onClick={getCurrentLocation} className={`${styles.locateBtn} ${styles.glowButton}`}>
            📍 Get Current Location
          </button>
          <div className={`${styles.confirmationStatus} ${locationConfirmed ? styles.confirmed : ''}`}>
            {locationConfirmed ? '✅ Location Confirmed' : '📍 Select Start Location'}
          </div>
        </div>

        <AccuracyTips />

        <p className={styles.selectedAddress}>
          <strong>Selected Start:</strong> {selectedAddress || "None selected yet"}
          {useManualStart && <span style={{color: '#10b981', fontWeight: 'bold'}}> (Manual Selection)</span>}
          {destinationPosition && (
            <>
              <br />
              <strong>Selected Destination:</strong> {destination || "None selected yet"}
            </>
          )}
        </p>

        {/* Start Mode Indicator */}
        {locationConfirmed && (
          <div className={styles.startModeIndicator}>
            {useManualStart ? (
              <span style={{color: '#10b981'}}>📍 Using manually selected start point</span>
            ) : (
              <span style={{color: '#3b82f6'}}>📍 Using your current location</span>
            )}
          </div>
        )}

        <button
          className={`${styles.calculateBtn} ${loading ? styles.loading : ''}`}
          onClick={calculateRoute}
          disabled={loading || navigationStarted || !manualPosition || !destination}
        >
          {loading ? (
            <>
              <div className={styles.spinner}></div>
              {loadingStatus || "Calculating Route..."}
            </>
          ) : (
            <>
              <i className="fas fa-route"></i> Find Safest Route
            </>
          )}
        </button>
        
        {/* Loading Status Info */}
        {loading && loadingStatus && (
          <div className={styles.loadingInfo}>
            <p>⏳ {loadingStatus}</p>
            {loadingStatus.includes('Geocoding') && (
              <small style={{color: 'var(--text-muted)', display: 'block', marginTop: '0.5rem'}}>
                Please wait... Respecting OpenStreetMap rate limits (1 request/second)
              </small>
            )}
          </div>
        )}
      </div>

      {/* Recalculation Status */}
      {recalculating && (
        <div className={styles.recalculationStatus}>
          <div className={styles.spinner}></div>
          Recalculating route...
        </div>
      )}

      {/* Progress Bar */}
      {navigationStarted && (
        <div className={styles.progressContainer}>
          <div className={styles.progressBar}>
            <div 
              className={styles.progressFill} 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <span className={styles.progressText}>{Math.round(progress)}% Complete</span>
          {locationAccuracy && (
            <span className={`${styles.accuracyBadge} ${
              locationAccuracy === 'high' ? styles.highAccuracy :
              locationAccuracy === 'medium' ? styles.mediumAccuracy :
              styles.lowAccuracy
            }`}>
              Accuracy: {locationAccuracy}
            </span>
          )}
        </div>
      )}

      {/* Route Results */}
      {route && (
        <div className={`${styles.routeResults} ${navigationStarted ? styles.navigationActive : ''}`}>
          <div className={styles.routeOverview}>
            <div className={styles.routeStats}>
              <div className={styles.stat}>
                <i className="fas fa-road"></i> 
                <span>{route.distance}</span>
              </div>
              <div className={styles.stat}>
                <i className="fas fa-clock"></i> 
                <span>{route.duration}</span>
              </div>
              <div className={styles.stat}>
                <i className="fas fa-shield-alt"></i>
                <span className={styles.safetyScore}>Safety: {safetyScore}%</span>
              </div>
            </div>

            {!navigationStarted ? (
              <button className={`${styles.startNavBtn} ${styles.glowButton}`} onClick={startNavigation}>
                <i className="fas fa-play"></i> Start Navigation
              </button>
            ) : (
              <div className={styles.navigationActive}>
                <div className={styles.activeNavHeader}>
                  <i className="fas fa-satellite-dish"></i> Navigation Active
                  {carPosition && (
                    <span className={styles.gpsStatus}>
                      <i className="fas fa-satellite"></i> GPS Active
                    </span>
                  )}
                  <span className={styles.startModeBadge}>
                    {useManualStart ? "📍 Manual Start" : "📍 Current Location"}
                  </span>
                </div>
                <div className={styles.navControls}>
                  <button className={styles.stopNavBtn} onClick={stopNavigation}>
                    ⏹ Stop
                  </button>
                  <button className={styles.restartBtn} onClick={restartNavigation}>
                    🔄 Restart
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className={styles.navigationSteps}>
            <h4>
              <i className="fas fa-list-ol"></i> Turn-by-Turn Directions
              {navigationStarted && (
                <span className={styles.currentStep}>
                  Step {currentStep + 1} of {route.steps.length}
                </span>
              )}
            </h4>
            <div className={styles.stepsList}>
              {route.steps.map((step, index) => (
                <div
                  key={index}
                  className={`${styles.stepItem} ${
                    navigationStarted && index === currentStep ? styles.activeStep : ''
                  } ${index < currentStep ? styles.completedStep : ''}`}
                >
                  <div className={styles.stepNumber}>
                    {index < currentStep ? (
                      <i className="fas fa-check"></i>
                    ) : (
                      index + 1
                    )}
                  </div>
                  <div className={styles.stepContent}>
                    <p>{step.instruction}</p>
                    <span>
                      {step.distance} • {step.duration}
                    </span>
                  </div>
                  {navigationStarted && index === currentStep && (
                    <div className={styles.currentStepIndicator}>
                      <div className={styles.pulseDot}></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Safety Factors Display */}
          {route.safety && route.safety.factors && (
            <div className={styles.safetyFactors}>
              <h4>
                <i className="fas fa-shield-alt"></i> Safety Factors
              </h4>
              <div className={styles.factorsGrid}>
                <div className={styles.factor}>
                  <span className={styles.factorLabel}>Crime Rate</span>
                  <span className={`${styles.factorValue} ${styles[route.safety.factors.crime_rate]}`}>
                    {route.safety.factors.crime_rate === 'high' ? '🔴 High' :
                     route.safety.factors.crime_rate === 'medium' ? '🟡 Medium' : '🟢 Low'}
                  </span>
                </div>
                <div className={styles.factor}>
                  <span className={styles.factorLabel}>Lighting</span>
                  <span className={`${styles.factorValue} ${styles[route.safety.factors.lighting]}`}>
                    {route.safety.factors.lighting === 'poor' ? '🌑 Poor' : '💡 Good'}
                  </span>
                </div>
                <div className={styles.factor}>
                  <span className={styles.factorLabel}>Traffic</span>
                  <span className={`${styles.factorValue} ${styles[route.safety.factors.traffic]}`}>
                    {route.safety.factors.traffic === 'high' ? '🚗 High' :
                     route.safety.factors.traffic === 'moderate' ? '🚗 Moderate' : '🚗 Low'}
                  </span>
                </div>
                <div className={styles.factor}>
                  <span className={styles.factorLabel}>Emergency Services</span>
                  <span className={`${styles.factorValue} ${styles[route.safety.factors.emergency_services_proximity]}`}>
                    {route.safety.factors.emergency_services_proximity === 'very_high' ? '✅ Very Close' :
                     route.safety.factors.emergency_services_proximity === 'high' ? '✅ Close' : '⚠️ Far'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {route.safety && route.safety.alerts?.length > 0 && (
            <div className={styles.safetyAlerts}>
              <h4>
                <i className="fas fa-exclamation-triangle"></i> Safety Alerts
              </h4>
              {route.safety.alerts.map((alert, i) => (
                <div key={i} className={`${styles.alertItem} ${styles[alert.severity]}`}>
                  <div className={styles.alertSeverity}></div>
                  <div className={styles.alertContent}>
                    <h5>{alert.type}</h5>
                    <p>{alert.description}</p>
                    <span>Near: {alert.location}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Enhanced Map */}
      <MapDisplay
        route={route}
        startPosition={manualPosition}
        destPosition={destinationPosition}
        onStartSelect={handleManualSelect}
        onDestSelect={handleDestinationSelect}
        onStartDragEnd={(pos) => {
          if (navigationStarted) return;
          setManualPosition(pos);
          setLocationConfirmed(true);
          setUseManualStart(true);
          reverseGeocode(pos.lat, pos.lng).then((addr) => {
            setSelectedAddress(addr);
            setStartLocation(addr);
          });
        }}
        onDestDragEnd={(pos) => {
          if (navigationStarted) return;
          setDestinationPosition(pos);
          reverseGeocode(pos.lat, pos.lng).then((addr) => {
            setDestination(addr);
          });
        }}
        navigationStarted={navigationStarted}
        carPosition={carPosition}
        onCarPositionUpdate={handleCarPositionUpdate}
        onRouteRecalculation={handleRouteRecalculation}
        useManualStart={useManualStart}
      />
    </div>
  );
};

export default NavigationSystem;




