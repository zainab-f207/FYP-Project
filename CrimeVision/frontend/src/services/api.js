// This file previously defined a local API client that hard-coded http://127.0.0.1:8000.
// To avoid duplicate/hard-coded hosts, delegate to the centralized apiService implementation
// which respects VITE_API_BASE_URL or infers a sensible default for local dev.
import apiService from './apiService_updated';

export { apiService };
export default apiService;
