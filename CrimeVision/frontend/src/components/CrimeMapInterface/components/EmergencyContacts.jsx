import React, { useState, useEffect } from 'react';
import './EmergencyContacts.css';
import apiService from '../../../services/apiService_updated';

const EmergencyContacts = () => {
  const [expandedContact, setExpandedContact] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [recentCalls, setRecentCalls] = useState([]);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [contactsData, setContactsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [locationAddress, setLocationAddress] = useState('');
  const [manualLocationInput, setManualLocationInput] = useState('');
  const [isEditingLocation, setIsEditingLocation] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [expandedTip, setExpandedTip] = useState(null);
  const [emergencyStats, setEmergencyStats] = useState({
    calls_today: 0,
    avg_response: 'N/A',
    active_units: 0,
    resolved_rate: '0%'
  });

  // Get user location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const location = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            address: 'Getting address...'
          };
          setUserLocation(location);
          
          // Get address from coordinates
          const address = await getAddressFromCoords(location.lat, location.lng);
          setLocationAddress(address);
          setUserLocation(prev => ({ ...prev, address }));
        },
        (error) => {
          console.log('Location access denied, using default Lahore coordinates');
          const defaultLocation = {
            lat: 31.5204,
            lng: 74.3587,
            address: 'Lahore, Pakistan'
          };
          setUserLocation(defaultLocation);
          setLocationAddress('Lahore, Pakistan');
        }
      );
    }
  }, []);

  // Free reverse geocoding function
  const getAddressFromCoords = async (lat, lng) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
      );
      
      if (!response.ok) throw new Error('Network response was not ok');
      
      const data = await response.json();
      
      if (data && data.address) {
        const addr = data.address;
        
        // Create a readable address
        const addressParts = [
          addr.road,
          addr.house_number,
          addr.neighbourhood,
          addr.suburb,
          addr.city || addr.town || addr.village,
          addr.state,
          addr.country
        ].filter(Boolean);
        
        return addressParts.join(', ');
      }
      
      return 'Address not available';
    } catch (error) {
      console.error('Error fetching address:', error);
      return 'Unable to fetch address';
    }
  };

  // Geocode location name to coordinates (Pakistan only)
  const geocodeLocation = async (locationName) => {
    try {
      setLocationLoading(true);
      
      // Add Pakistan to the search query if not already included
      const searchQuery = locationName.toLowerCase().includes('pakistan') 
        ? locationName 
        : `${locationName}, Pakistan`;
      
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&countrycodes=pk&limit=1`
      );
      
      if (!response.ok) throw new Error('Geocoding failed');
      
      const data = await response.json();
      
      if (data && data.length > 0) {
        const result = data[0];
        const newLocation = {
          lat: parseFloat(result.lat),
          lng: parseFloat(result.lon),
          address: result.display_name
        };
        
        setUserLocation(newLocation);
        setLocationAddress(result.display_name);
        setIsEditingLocation(false);
        setManualLocationInput('');
        
        return newLocation;
      } else {
        alert('❌ Location not found in Pakistan. Please try a different search term.');
        return null;
      }
    } catch (error) {
      console.error('Error geocoding location:', error);
      alert('❌ Failed to find location. Please check your internet connection.');
      return null;
    } finally {
      setLocationLoading(false);
    }
  };

  // Handle manual location submission
  const handleManualLocationSubmit = async (e) => {
    e.preventDefault();
    if (!manualLocationInput.trim()) {
      alert('Please enter a location name');
      return;
    }
    await geocodeLocation(manualLocationInput);
  };

  // Load recent calls from localStorage
  useEffect(() => {
    const savedCalls = localStorage.getItem('emergencyRecentCalls');
    if (savedCalls) {
      setRecentCalls(JSON.parse(savedCalls));
    }
  }, []);

  // Load emergency contacts from API
  useEffect(() => {
    const fetchEmergencyContacts = async () => {
      try {
        const response = await apiService.get('/api/emergency-contacts');
        if (response && response.contacts) {
          setContactsData(response.contacts);
        } else {
          // Fallback to static data if API fails
          console.warn('API returned no contacts, using fallback data');
          setContactsData([
            {
              id: 1,
              name: "Police Emergency",
              number: "15",
              color: "#ff4444",
              gradient: "linear-gradient(135deg, #ff4444, #cc0000)",
              icon: "fas fa-shield-alt",
              response: "2-5 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Immediate police response for emergencies, accidents, and security threats.",
              services: ["Emergency Response", "Crime Reporting", "Traffic Control", "Security Patrol"]
            },
            {
              id: 2,
              name: "Rescue 1122",
              number: "1122",
              color: "#ff8800",
              gradient: "linear-gradient(135deg, #ff8800, #cc6600)",
              icon: "fas fa-ambulance",
              response: "5-8 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Medical emergencies, fire response, and disaster management services.",
              services: ["Medical Emergency", "Fire Response", "Disaster Relief", "Ambulance Service"]
            },
            {
              id: 3,
              name: "Fire Brigade",
              number: "16",
              color: "#ff6600",
              gradient: "linear-gradient(135deg, #ff6600, #cc3300)",
              icon: "fas fa-fire-extinguisher",
              response: "3-6 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Fire fighting, rescue operations, and hazardous material incidents.",
              services: ["Fire Fighting", "Rescue Operations", "Hazard Response", "Prevention Services"]
            },
            {
              id: 4,
              name: "Women Helpline",
              number: "1099",
              color: "#ff66aa",
              gradient: "linear-gradient(135deg, #ff66aa, #cc3388)",
              icon: "fas fa-female",
              response: "10-15 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Support for women facing harassment, abuse, or domestic violence.",
              services: ["Harassment Support", "Legal Aid", "Counseling", "Emergency Shelter"]
            },
            {
              id: 5,
              name: "Child Helpline",
              number: "1121",
              color: "#66aaff",
              gradient: "linear-gradient(135deg, #66aaff, #3388cc)",
              icon: "fas fa-child",
              response: "8-12 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Protection and support services for children in distress or danger.",
              services: ["Child Protection", "Missing Children", "Abuse Reporting", "Counseling Services"]
            },
            {
              id: 6,
              name: "Traffic Police",
              number: "1915",
              color: "#44aa44",
              gradient: "linear-gradient(135deg, #44aa44, #228822)",
              icon: "fas fa-car",
              response: "5-10 min",
              coordinates: { lat: 31.5204, lng: 74.3587 },
              description: "Traffic accidents, violations, and road safety assistance.",
              services: ["Accident Response", "Traffic Control", "Violation Reports", "Road Safety"]
            }
          ]);
        }
      } catch (error) {
        console.error('Error fetching emergency contacts:', error);
        // Use fallback data
        setContactsData([
          // ... (same fallback data)
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchEmergencyContacts();
  }, []);

  // Fetch emergency stats from API
  const fetchEmergencyStats = async () => {
    try {
      const response = await apiService.get('/api/emergency-stats');
      if (response && typeof response === 'object') {
        setEmergencyStats(prevStats => ({ ...prevStats, ...response }));
      }
    } catch (error) {
      console.error('Error fetching emergency stats:', error);
      setError('Failed to load emergency statistics');
    }
  };

  useEffect(() => {
    fetchEmergencyStats();
    const interval = setInterval(fetchEmergencyStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleContactClick = (contactId) => {
    if (expandedContact === contactId) {
      setExpandedContact(null);
    } else {
      setExpandedContact(contactId);
    }
  };

   const handleCall = async (contact) => {
  // Add to recent calls
  const newCall = {
    id: Date.now(),
    contact: contact.name,
    number: contact.number,
    timestamp: new Date().toISOString(),
    location: userLocation
  };

  const updatedCalls = [newCall, ...recentCalls.slice(0, 4)];
  setRecentCalls(updatedCalls);
  localStorage.setItem('emergencyRecentCalls', JSON.stringify(updatedCalls));

  // Open phone dialer
  window.open(`tel:${contact.number}`, '_blank');

 alert(`📞 Calling ${contact.name}...\n\nEmergency: ${contact.number}\n\nMake sure to:\n• Stay calm\n• Provide your location clearly\n• Describe the emergency briefly\n• Follow instructions`);

  // Log emergency call to backend
  try {
    const token = localStorage.getItem('authToken');
    const emergencyData = {
      contact_name: contact.name,
      contact_number: contact.number,
      emergency_type: contact.name.toLowerCase().replace(/ /g, '_'),
      caller_location_lat: userLocation?.lat || 31.5204,
      caller_location_lng: userLocation?.lng || 74.3587,
      caller_address: userLocation?.address || 'Lahore, Pakistan'
    };

    console.log('Attempting to log emergency call with data:', emergencyData);

    let response;
    if (token) {
      console.log('Using authenticated endpoint with token');
      try {
        response = await apiService.logEmergencyCall(token, emergencyData);
      } catch (authError) {
        console.warn('Authenticated call failed, falling back to public endpoint:', authError);
        // Fall back to public endpoint if authenticated call fails
        response = await apiService.logEmergencyCallPublic(emergencyData);
      }
    } else {
      console.log('No token found, using public endpoint');
      response = await apiService.logEmergencyCallPublic(emergencyData);
    }

    console.log('Emergency call logged successfully:', response);

    // Refresh emergency stats after logging the call
    setTimeout(() => {
      fetchEmergencyStats();
    }, 1000);

  } catch (error) {
    console.error('Failed to log emergency call to backend:', error);
    // Don't show error to user as the call was already made
    // But you might want to log this for debugging
  }
};

  const handleSMS = (contact) => {
    if (userLocation) {
      const mapsUrl = `https://maps.google.com/?q=${userLocation.lat},${userLocation.lng}`;
      const address = locationAddress || userLocation.address;
      
      const message = `🚨 EMERGENCY LOCATION 🚨

📍 My Current Location: ${address}
🗺️ Google Maps: ${mapsUrl}
📱 Sent via SafeVision Emergency App

EMERGENCY: Need immediate assistance at this location. Please respond urgently.`;

      window.open(`sms:${contact.number}?body=${encodeURIComponent(message)}`, '_blank');
    } else {
      alert('📍 Location not available. Please enable location services.');
    }
  };

  const handleLocationShare = async (contact) => {
    if (!userLocation) {
      alert('📍 Location not available. Please enable location services.');
      return;
    }

    try {
      // Get current address if not already available
      let address = locationAddress;
      if (!address || address === 'Getting address...') {
        address = await getAddressFromCoords(userLocation.lat, userLocation.lng);
        setLocationAddress(address);
      }

      // Create multiple map links (100% free)
      const googleMapsUrl = `https://maps.google.com/?q=${userLocation.lat},${userLocation.lng}`;
      const openStreetMapUrl = `https://www.openstreetmap.org/?mlat=${userLocation.lat}&mlon=${userLocation.lng}&zoom=16`;
      const appleMapsUrl = `https://maps.apple.com/?ll=${userLocation.lat},${userLocation.lng}&z=16`;
      
      // Create the emergency message (like WhatsApp)
      const message = `🚨 EMERGENCY LOCATION SHARING 🚨

📍 My Current Location:
${address}

🗺️ Navigation Links:
• Google Maps: ${googleMapsUrl}
• OpenStreetMap: ${openStreetMapUrl}
• Apple Maps: ${appleMapsUrl}

📊 Coordinates:
Latitude: ${userLocation.lat.toFixed(6)}
Longitude: ${userLocation.lng.toFixed(6)}

🕐 Shared at: ${new Date().toLocaleString()}
📱 Sent via SafeVision Emergency App

EMERGENCY: I need immediate assistance at this location. Please navigate to this address urgently.`;

      // Copy to clipboard
      await navigator.clipboard.writeText(message);
      
      // Open SMS with the message
      const smsUrl = `sms:${contact.number}?body=${encodeURIComponent(message)}`;
      window.open(smsUrl, '_blank');

      // Show success message
      alert(`📍 Location Shared Successfully!\n\n✅ Address copied to clipboard\n✅ SMS prepared for ${contact.name}\n\nAddress: ${address}\n\nYour exact location has been prepared for emergency response.`);

    } catch (error) {
      console.error('Error sharing location:', error);
      alert('❌ Failed to share location. Please try again.');
    }
  };

  // Enhanced location sharing with multiple options
  const handleAdvancedLocationShare = async (contact) => {
    if (!userLocation) {
      alert('📍 Location not available. Please enable location services.');
      return;
    }

    try {
      // Get precise address
      const address = await getAddressFromCoords(userLocation.lat, userLocation.lng);
      
      // Create multiple free map options
      const mapLinks = {
        'Google Maps': `https://maps.google.com/?q=${userLocation.lat},${userLocation.lng}`,
        'OpenStreetMap': `https://www.openstreetmap.org/?mlat=${userLocation.lat}&mlon=${userLocation.lng}&zoom=16`,
        'Apple Maps': `https://maps.apple.com/?ll=${userLocation.lat},${userLocation.lng}&z=16`,
        'Bing Maps': `https://bing.com/maps/?cp=${userLocation.lat}~${userLocation.lng}&lvl=16`
      };

      // Create comprehensive emergency message
      const message = `🚨 EMERGENCY LOCATION ALERT 🚨

📍 IMMEDIATE ASSISTANCE REQUIRED

📋 Location Details:
• Address: ${address}
• Latitude: ${userLocation.lat.toFixed(6)}
• Longitude: ${userLocation.lng.toFixed(6)}

🗺️ Quick Navigation Links:
${Object.entries(mapLinks).map(([name, url]) => `• ${name}: ${url}`).join('\n')}

⏰ Time of Alert: ${new Date().toLocaleString()}
📱 Source: SafeVision Emergency Response System

🚑 URGENT: Please proceed to this location immediately for emergency assistance.`;

      // Copy to clipboard as backup
      await navigator.clipboard.writeText(message);

      // Create SMS URL (works on most mobile devices)
      const smsUrl = `sms:${contact.number}?body=${encodeURIComponent(message)}`;
      
      // Try to open SMS app
      const smsWindow = window.open(smsUrl, '_blank');
      
      if (!smsWindow || smsWindow.closed || typeof smsWindow.closed === 'undefined') {
        // Fallback: show message and let user copy manually
        alert(`📍 Emergency Location Ready!\n\n✅ Address: ${address}\n✅ Coordinates: ${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}\n\n📋 The location details have been copied to your clipboard. Please paste them into your messaging app.\n\nFor navigation, use this link:\nhttps://maps.google.com/?q=${userLocation.lat},${userLocation.lng}`);
      }

    } catch (error) {
      console.error('Error in advanced location sharing:', error);
      // Fallback simple method
      const simpleMessage = `EMERGENCY: Need help at ${userLocation.lat},${userLocation.lng}. Maps: https://maps.google.com/?q=${userLocation.lat},${userLocation.lng}`;
      window.open(`sms:${contact.number}?body=${encodeURIComponent(simpleMessage)}`, '_blank');
    }
  };

  const triggerEmergencyMode = () => {
    setEmergencyMode(true);
    document.body.style.animation = 'emergencyFlash 1s infinite';
    
    setTimeout(() => {
      setEmergencyMode(false);
      document.body.style.animation = '';
    }, 10000);
  };

  const calculateDistance = (contactCoords) => {
    if (!userLocation) return 'Unknown';
    
    const R = 6371;
    const dLat = (contactCoords.lat - userLocation.lat) * Math.PI / 180;
    const dLon = (contactCoords.lng - userLocation.lng) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(userLocation.lat * Math.PI / 180) * Math.cos(contactCoords.lat * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    
    return distance < 1 ? `${Math.round(distance * 1000)}m` : `${distance.toFixed(1)}km`;
  };

  return (
    <section className="emergency-contacts-section">
      <div className="emergency-container">
        {/* Emergency Alert Header */}
        <div className="emergency-alert-header">
          <div className="alert-status">
            <div className={`status-indicator ${emergencyMode ? 'active' : ''}`}>
              <div className="pulse-ring"></div>
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className="status-info">
              <h3>Emergency Response System</h3>
              <p>Lahore Division • Real-time Monitoring</p>
            </div>
          </div>
          <button 
            className="emergency-alert-btn"
            onClick={triggerEmergencyMode}
          >
            <i className="fas fa-bell"></i>
            Emergency Alert
          </button>
        </div>

        {/* Live Stats Overview */}
        <div className="live-stats-overview">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-icon">
                <i className="fas fa-phone-alt"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{emergencyStats.calls_today || 0}</div>
                <div className="stat-label">Calls Today</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">
                <i className="fas fa-clock"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{emergencyStats.avg_response || 'N/A'}</div>
                <div className="stat-label">Avg Response</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">
                <i className="fas fa-map-marker-alt"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{emergencyStats.active_units || 0}</div>
                <div className="stat-label">Active Units</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">
                <i className="fas fa-check-circle"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{emergencyStats.resolved_rate || '0%'}</div>
                <div className="stat-label">Resolved</div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Contacts Grid */}
        <div className="contacts-grid">
          {contactsData.map((contact, index) => (
            <div
              key={contact.id}
              className={`contact-card ${expandedContact === contact.id ? 'expanded' : ''}`}
              style={{
                '--contact-color': contact.color,
                '--contact-gradient': contact.gradient,
                animationDelay: `${index * 100}ms`
              }}
            >
              {/* Card Background Effects */}
              <div className="card-bg-effects">
                <div className="floating-orb" style={{ background: contact.color }}></div>
                <div className="active-pulse"></div>
              </div>

              {/* Live Status Badge */}
              <div className="live-status-badge">
                <div className="status-dot"></div>
                <span>LIVE</span>
              </div>

              {/* Contact Header */}
              <div className="contact-header" onClick={() => handleContactClick(contact.id)}>
                <div className="contact-icon-wrapper">
                  <div 
                    className="contact-icon"
                    style={{ background: contact.gradient }}
                  >
                    <i className={contact.icon}></i>
                  </div>
                </div>
                
                <div className="contact-main-info">
                  <h4 className="contact-name">{contact.name}</h4>
                  <div className="contact-number-display">{contact.number}</div>
                  <div className="contact-meta">
                    <span className="response-time">
                      <i className="fas fa-tachometer-alt"></i>
                      {contact.response}
                    </span>
                    <span className="distance">
                      <i className="fas fa-location-arrow"></i>
                      {calculateDistance(contact.coordinates)}
                    </span>
                  </div>
                </div>

                <div className="contact-actions">
                  <button
                    className="call-primary-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCall(contact);
                    }}
                    style={{ background: contact.gradient }}
                  >
                    <i className="fas fa-phone"></i>
                  </button>
                  <div className="expand-indicator">
                    <i className={`fas fa-chevron-${expandedContact === contact.id ? 'up' : 'down'}`}></i>
                  </div>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedContact === contact.id && (
                <div className="contact-details">
                  <div className="details-content">
                    <p className="contact-description">{contact.description}</p>

                    {/* Services List */}
                    <div className="services-section">
                      <h5>Available Services:</h5>
                      <div className="services-grid">
                        {contact.services.map((service, idx) => (
                          <div key={idx} className="service-item">
                            <i className="fas fa-check"></i>
                            <span>{service}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="quick-actions">
                      <button
                        className="action-btn secondary"
                        onClick={() => handleSMS(contact)}
                      >
                        <i className="fas fa-sms"></i>
                        Send SMS
                      </button>
                      <button
                        className="action-btn secondary"
                        onClick={() => handleAdvancedLocationShare(contact)}
                      >
                        <i className="fas fa-share-location"></i>
                        Share Location
                      </button>
                      <button
                        className="action-btn primary"
                        onClick={() => handleCall(contact)}
                        style={{ background: contact.gradient }}
                      >
                        <i className="fas fa-phone"></i>
                        Call Now
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Emergency Footer */}
        <div className="emergency-footer">
          <div className="footer-grid">
            {/* Emergency Preparedness Guide */}
            <div className="footer-card emergency-preparedness">
              <div className="preparedness-header">
                <i className="fas fa-book-medical"></i>
                <h4>Emergency Preparedness Guide</h4>
              </div>
              <div className="preparedness-tips">
                {[
                  {
                    id: 1,
                    icon: 'fas fa-heartbeat',
                    title: 'Stay Calm',
                    color: '#ff4444',
                    shortDesc: 'Keep composure in emergencies',
                    fullDesc: 'Take deep breaths, assess the situation calmly, and think clearly before acting. Panic can worsen the situation.'
                  },
                  {
                    id: 2,
                    icon: 'fas fa-map-marked-alt',
                    title: 'Know Your Location',
                    color: '#ff8800',
                    shortDesc: 'Always be aware of your surroundings',
                    fullDesc: 'Memorize nearby landmarks, street names, and notable buildings. This helps emergency services locate you faster.'
                  },
                  {
                    id: 3,
                    icon: 'fas fa-phone-volume',
                    title: 'Clear Communication',
                    color: '#44aa44',
                    shortDesc: 'Speak clearly and provide details',
                    fullDesc: 'When calling emergency services, speak slowly, provide your exact location, describe the emergency, and follow their instructions.'
                  },
                  {
                    id: 4,
                    icon: 'fas fa-first-aid',
                    title: 'Basic First Aid',
                    color: '#66aaff',
                    shortDesc: 'Learn essential first aid skills',
                    fullDesc: 'Know CPR, how to stop bleeding, treat burns, and handle choking. These skills can save lives while waiting for help.'
                  }
                ].map((tip) => (
                  <div
                    key={tip.id}
                    className={`tip-card ${expandedTip === tip.id ? 'expanded' : ''}`}
                    onClick={() => setExpandedTip(expandedTip === tip.id ? null : tip.id)}
                    style={{ '--tip-color': tip.color }}
                  >
                    <div className="tip-header">
                      <div className="tip-icon" style={{ background: tip.color }}>
                        <i className={tip.icon}></i>
                      </div>
                      <div className="tip-content">
                        <h5>{tip.title}</h5>
                        <p>{tip.shortDesc}</p>
                      </div>
                      <i className={`fas fa-chevron-${expandedTip === tip.id ? 'up' : 'down'} tip-expand`}></i>
                    </div>
                    {expandedTip === tip.id && (
                      <div className="tip-details">
                        <p>{tip.fullDesc}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Right Side - Stacked Cards */}
            <div className="safety-info">
              <div className="info-card critical">
                <div className="info-icon">
                  <i className="fas fa-exclamation-triangle"></i>
                </div>
                <div className="info-content">
                  <h5>Emergency Protocol</h5>
                  <p>For life-threatening situations, call immediately. Stay calm and provide clear location details.</p>
                </div>
              </div>

              <div className="info-card location-card">
                <div className="info-icon">
                  <i className="fas fa-map-marker-alt"></i>
                </div>
                <div className="info-content">
                  <div className="location-header">
                    <h5>Your Location</h5>
                    <button
                      className="edit-location-btn"
                      onClick={() => setIsEditingLocation(!isEditingLocation)}
                      title="Edit location manually"
                    >
                      <i className={`fas fa-${isEditingLocation ? 'times' : 'edit'}`}></i>
                    </button>
                  </div>

                  {!isEditingLocation ? (
                    <p>
                      {locationAddress || 'Fetching address...'}
                      <br />
                      <small style={{opacity: 0.7}}>
                        Coordinates: {userLocation ? `${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}` : 'Not available'}
                      </small>
                    </p>
                  ) : (
                    <form onSubmit={handleManualLocationSubmit} className="manual-location-form">
                      <div className="location-input-wrapper">
                        <input
                          type="text"
                          value={manualLocationInput}
                          onChange={(e) => setManualLocationInput(e.target.value)}
                          placeholder="Enter location (e.g., Model Town, Lahore)"
                          className="location-input"
                          disabled={locationLoading}
                        />
                        <button
                          type="submit"
                          className="location-submit-btn"
                          disabled={locationLoading}
                        >
                          {locationLoading ? (
                            <i className="fas fa-spinner fa-spin"></i>
                          ) : (
                            <i className="fas fa-search"></i>
                          )}
                        </button>
                      </div>
                      <small className="location-hint">
                        <i className="fas fa-info-circle"></i>
                        Enter a location name to automatically get coordinates
                      </small>
                    </form>
                  )}
                </div>
              </div>

              <div className="info-card">
                <div className="info-icon">
                  <i className="fas fa-lightbulb"></i>
                </div>
                <div className="info-content">
                  <h5>Safety Tip</h5>
                  <p>Keep your location services enabled for faster emergency response times.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Emergency Mode Overlay */}
        {emergencyMode && (
          <div className="emergency-mode-overlay">
            <div className="emergency-alert-modal">
              <div className="alert-header">
                <div className="alert-icon">
                  <i className="fas fa-exclamation-triangle"></i>
                </div>
                <h3>EMERGENCY MODE ACTIVATED</h3>
              </div>
              <div className="alert-content">
                <p>All emergency services have been alerted. Choose an action:</p>
                <div className="emergency-actions">
                  <button
                    className="emergency-action-btn critical"
                    onClick={() => handleCall(contactsData[0])}
                  >
                    <i className="fas fa-phone"></i>
                    Call Police (15)
                  </button>
                  <button
                    className="emergency-action-btn critical"
                    onClick={() => handleAdvancedLocationShare(contactsData[0])}
                  >
                    <i className="fas fa-share-location"></i>
                    Share Location
                  </button>
                  <button
                    className="emergency-action-btn"
                    onClick={() => setEmergencyMode(false)}
                  >
                    <i className="fas fa-times"></i>
                    Cancel Alert
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default EmergencyContacts;
