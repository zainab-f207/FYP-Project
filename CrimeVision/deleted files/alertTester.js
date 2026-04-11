// src/utils/alertTester.js
export const testOfflineAlerts = async () => {
  // Simulate offline scenario
  const originalFetch = window.fetch;
  window.fetch = () => Promise.reject(new Error('Network offline'));
  
  try {
    // Trigger background monitoring
    await fetch('/api/test/trigger-monitoring', { 
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch (error) {
    console.log('✅ Offline scenario simulated - scheduler should handle this');
  } finally {
    window.fetch = originalFetch;
  }
};

export const testRiskZoneAlerts = async (token, testLocation) => {
  // Test location in known high-risk area
  const testData = {
    latitude: 31.5204, // Known risk area coordinates
    longitude: 74.3587,
    address: "Test High Risk Zone, Lahore",
    check_immediate: true
  };
  
  try {
    const response = await apiService.checkLocationForAlerts(token, testData);
    console.log('📍 Risk Zone Alert Test Result:', response);
    return response;
  } catch (error) {
    console.error('❌ Risk zone alert test failed:', error);
  }
};