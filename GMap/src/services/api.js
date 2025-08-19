import axios from 'axios';

// Base API configuration
const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout for long-running operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service functions
export const apiService = {
  // Health check
  async checkHealth() {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  },

  // Get available villages
  async getVillages() {
    try {
      const response = await api.get('/villages');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch villages: ${error.message}`);
    }
  },

  // Get village structure information
  async getVillageStructure(villageName) {
    try {
      const response = await api.get(`/village/${villageName}/structure`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch village structure: ${error.message}`);
    }
  },

  // Run comparison analysis
  async runComparison(villageName, chosenIndex, comparisonMethod = 'standard') {
    try {
      const response = await api.post('/compare', {
        village_name: villageName,
        chosen_index: chosenIndex,
        comparison_method: comparisonMethod,
      });
      return response.data;
    } catch (error) {
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      throw new Error(`Comparison failed: ${error.message}`);
    }
  },

  // Generate PDF report
  async generatePDF(sessionId) {
    try {
      const response = await api.post(`/generate-pdf/${sessionId}`);
      return response.data;
    } catch (error) {
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      throw new Error(`PDF generation failed: ${error.message}`);
    }
  },

  // Download PDF
  async downloadPDF(filename) {
    try {
      const response = await api.get(`/download-pdf/${filename}`, {
        responseType: 'blob',
      });
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      return { success: true };
    } catch (error) {
      throw new Error(`PDF download failed: ${error.message}`);
    }
  },
};

// Error handler for API responses
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    const { status, data } = error.response;
    return {
      status,
      message: data.error || 'An error occurred',
      details: data.traceback || null,
    };
  } else if (error.request) {
    // Request was made but no response received
    return {
      status: 0,
      message: 'No response from server. Please check if the backend is running.',
      details: null,
    };
  } else {
    // Something else happened
    return {
      status: -1,
      message: error.message || 'Unknown error occurred',
      details: null,
    };
  }
};

export default api;