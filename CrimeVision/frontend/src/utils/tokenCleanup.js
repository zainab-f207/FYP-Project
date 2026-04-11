// Token cleanup utility
export const cleanupInvalidTokens = () => {
  console.log('🔍 Checking for invalid tokens...');
  
  const tokenKeys = [
    'SafeVision_token',
    'auth_token',
    'user_token',
    'token'
  ];
  
  const userKeys = [
    'SafeVision_user',
    'auth_user',
    'user_data',
    'current_user'
  ];
  
  let cleanedCount = 0;
  
  // Check all possible token storage locations
  tokenKeys.forEach(key => {
    try {
      const token = localStorage.getItem(key) || sessionStorage.getItem(key);
      if (token) {
        // Basic token validation
        if (token.length < 10 || !token.includes('.')) {
          console.log(`🗑️ Removing invalid token format from ${key}`);
          localStorage.removeItem(key);
          sessionStorage.removeItem(key);
          cleanedCount++;
        }
      }
    } catch (error) {
      console.log(`⚠️ Error checking token ${key}:`, error);
    }
  });
  
  // Clean up orphaned user data
  userKeys.forEach(key => {
    try {
      const userData = localStorage.getItem(key) || sessionStorage.getItem(key);
      if (userData) {
        const user = JSON.parse(userData);
        if (!user || !user.username) {
          console.log(`🗑️ Removing invalid user data from ${key}`);
          localStorage.removeItem(key);
          sessionStorage.removeItem(key);
          cleanedCount++;
        }
      }
    } catch (error) {
      console.log(`🗑️ Removing corrupted user data from ${key}`);
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
      cleanedCount++;
    }
  });
  
  console.log(`✅ Token cleanup completed: ${cleanedCount} items cleaned`);
  return cleanedCount;
};

// Run cleanup on import
cleanupInvalidTokens();
