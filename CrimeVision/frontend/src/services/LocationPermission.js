// LocationPermission.js
// Check if permissions API is supported
const isPermissionsSupported = () => {
  return navigator.permissions && typeof navigator.permissions.query === 'function';
};

// Function to create and handle custom permission prompt
function createPermissionPrompt() {
  return new Promise((resolve) => {
    // Create modal container
    const modalContainer = document.createElement('div');
    modalContainer.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      backdrop-filter: blur(4px);
    `;

    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
      background-color: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      max-width: 400px;
      width: 90%;
      text-align: center;
    `;

    // Create icon
    const icon = document.createElement('div');
    icon.style.cssText = `
      font-size: 3rem;
      margin-bottom: 1rem;
    `;
    icon.textContent = '📍';

    // Create title
    const title = document.createElement('h3');
    title.style.cssText = `
      margin: 0 0 1rem 0;
      color: #1f2937;
      font-size: 1.5rem;
    `;
    title.textContent = 'Location Access Required';

    // Create message
    const message = document.createElement('p');
    message.style.cssText = `
      margin: 0 0 1.5rem 0;
      color: #4b5563;
      line-height: 1.5;
    `;
    message.innerHTML = `
      SafeVision needs access to your location to:
      <br>• Show your current position
      <br>• Calculate safe routes
      <br>• Provide real-time navigation
      <br>• Alert you about nearby safety concerns
    `;

    // Create buttons container
    const buttonsContainer = document.createElement('div');
    buttonsContainer.style.cssText = `
      display: flex;
      gap: 1rem;
      justify-content: center;
    `;

    // Create allow button
    const allowButton = document.createElement('button');
    allowButton.style.cssText = `
      padding: 0.75rem 1.5rem;
      background-color: #10b981;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      transition: background-color 0.2s;
    `;
    allowButton.textContent = 'Allow Location Access';
    allowButton.onmouseover = () => allowButton.style.backgroundColor = '#059669';
    allowButton.onmouseout = () => allowButton.style.backgroundColor = '#10b981';

    // Create deny button
    const denyButton = document.createElement('button');
    denyButton.style.cssText = `
      padding: 0.75rem 1.5rem;
      background-color: #ef4444;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      transition: background-color 0.2s;
    `;
    denyButton.textContent = 'Not Now';
    denyButton.onmouseover = () => denyButton.style.backgroundColor = '#dc2626';
    denyButton.onmouseout = () => denyButton.style.backgroundColor = '#ef4444';

    // Setup event handlers
    allowButton.onclick = () => {
      document.body.removeChild(modalContainer);
      resolve(true);
    };

    denyButton.onclick = () => {
      document.body.removeChild(modalContainer);
      resolve(false);
    };

    // Assemble the modal
    buttonsContainer.appendChild(allowButton);
    buttonsContainer.appendChild(denyButton);
    modalContent.appendChild(icon);
    modalContent.appendChild(title);
    modalContent.appendChild(message);
    modalContent.appendChild(buttonsContainer);
    modalContainer.appendChild(modalContent);

    // Add to document
    document.body.appendChild(modalContainer);
  });
}

// Function to request location with ACCURACY THRESHOLD strategy
// Uses watchPosition to get continuous updates until accuracy threshold is met
const requestLocationWithHighAccuracy = () => {
  return new Promise((resolve, reject) => {
    console.log(`🎯 Requesting HIGH ACCURACY location with accuracy threshold strategy...`);

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
        console.log(`✅ Returning best position found (accuracy: ${bestPosition.coords.accuracy.toFixed(2)}m)`);
        resolve(bestPosition);
      } else {
        const error = new GeolocationPositionError();
        error.code = 3;
        error.message = 'Timeout expired - no position available';
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
          cleanup();
          resolve(position);
        } else if (accuracy < 100) {
          console.log(`🟢 Good accuracy: ${accuracy.toFixed(2)}m`);
        } else if (accuracy < 200) {
          console.log(`🟡 Medium accuracy: ${accuracy.toFixed(2)}m`);
        } else {
          console.log(`🟠 Low accuracy: ${accuracy.toFixed(2)}m`);
        }
      },
      (error) => {
        console.error(`❌ Location watch error:`, error.code, error.message);

        // If we have a best position, use it
        if (bestPosition) {
          console.log(`✅ Using best position found so far (accuracy: ${bestPosition.coords.accuracy.toFixed(2)}m)`);
          cleanup();
          resolve(bestPosition);
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

export async function requestLocationPermission() {
  try {
    // Show custom prompt first
    const userAccepted = await createPermissionPrompt();
    if (!userAccepted) {
      console.log("User declined location access in custom prompt");
      return false;
    }

    // Check existing permissions if supported
    if (isPermissionsSupported()) {
      const status = await navigator.permissions.query({ name: "geolocation" });
      
      if (status.state === "granted") {
        console.log("Location permission already granted");
        return true;
      }
      
      if (status.state === "denied") {
        alert("Location access is blocked. Please enable location services in your browser settings to use navigation features.");
        return false;
      }
    }

    // Request location access
    try {
      await requestLocationWithHighAccuracy();
      console.log("✅ Location permission granted and location acquired");
      return true;
    } catch (error) {
      console.error("❌ Location permission error:", error);

      // Handle different error types
      if (error.code === 1) { // PERMISSION_DENIED
        alert("❌ Location access is required for navigation.\n\nPlease enable location services in your browser settings:\n1. Click the lock icon in the address bar\n2. Allow location access\n3. Refresh the page");
      } else if (error.code === 2) { // POSITION_UNAVAILABLE
        alert("⚠️ Unable to detect your location.\n\nPlease check:\n1. Your device's location services are enabled\n2. You have a clear view of the sky (for GPS)\n3. Try moving to a different location");
      } else if (error.code === 3) { // TIMEOUT
        alert("⏱️ Location request timed out.\n\nThis can happen if:\n1. GPS signal is weak\n2. You're indoors\n3. Your device's location services are slow\n\nPlease try again or enable high-speed location services.");
      } else if (error.message && error.message.includes("after")) {
        // Multiple attempts failed
        alert("⏱️ Location request failed after multiple attempts.\n\nPlease:\n1. Check your internet connection\n2. Ensure location services are enabled\n3. Try again in a few moments");
      } else {
        alert("❌ Could not access your location.\n\nPlease check your device settings and try again.");
      }

      return false;
    }
  } catch (error) {
    console.error("Permission check error:", error);
    alert("Your browser does not support location permissions. Navigation features may not work correctly.");
    return false;
  }
}

// Helper function to check if location services are enabled
export async function checkLocationServicesEnabled() {
  try {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return false;
    }

    const position = await requestLocationWithHighAccuracy();
    return position ? true : false;
  } catch (error) {
    return false;
  }
}
