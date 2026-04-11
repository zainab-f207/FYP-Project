import axios from 'axios';

// Use absolute backend URL or rely on Vite proxy (port 3000)
// In dev, vite.config.js proxies '/api' to 'http://localhost:8000'
const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 600000, // 10 minutes timeout for large OCR operations (increased from 5 min)
    // Do NOT set 'Content-Type' for FormData; the browser sets correct boundary automatically
});

export const ocrService = {
    /**
     * Extract text from uploaded image
     * @param {File} file - Image file to process
     * @returns {Promise} - OCR result with text and confidence
     */
    extractText: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Let axios/browser set proper multipart boundaries
            console.log('Sending OCR request for file:', file.name, `(${(file.size / (1024*1024)).toFixed(2)}MB)`);
            const startTime = Date.now();
            
            const response = await api.post('/api/ocr/extract', formData);
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            console.log(`OCR response received in ${duration}s`);
            
            return response.data;
        } catch (error) {
            console.error('OCR request error:', error);
            if (error.response) {
                throw new Error(error.response.data.detail || 'OCR extraction failed');
            } else if (error.request) {
                throw new Error('No response from server. Please ensure the backend is running.');
            } else {
                throw new Error('Error setting up the request');
            }
        }
    },

    /**
     * Check API health status
     * @returns {Promise} - Health status
     */
    checkHealth: async () => {
        try {
            const response = await api.get('/api/health');
            return response.data;
        } catch (error) {
            throw new Error('Failed to check API health');
        }
    },
};

export default api;
