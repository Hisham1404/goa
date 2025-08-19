import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaSearch, FaDownload, FaSpinner, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';
import { MdMap, MdCompare, MdPictureAsPdf } from 'react-icons/md';
import { apiService, handleApiError } from '../services/api';
import toast from 'react-hot-toast';

const MapComparisonDashboard = () => {
  // State management
  const [villages, setVillages] = useState([]);
  const [selectedVillage, setSelectedVillage] = useState('');
  const [villageStructure, setVillageStructure] = useState(null);
  const [chosenIndex, setChosenIndex] = useState('');
  const [comparisonMethod, setComparisonMethod] = useState('standard');
  const [isLoading, setIsLoading] = useState(false);
  const [comparisonResults, setComparisonResults] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isPdfGenerating, setIsPdfGenerating] = useState(false);

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Check backend health
      const healthData = await apiService.checkHealth();
      setBackendHealth(healthData);
      
      if (healthData.success) {
        // Load villages
        const villagesData = await apiService.getVillages();
        setVillages(villagesData.villages || []);
        toast.success('Backend connected successfully!');
      }
    } catch (error) {
      const errorInfo = handleApiError(error);
      toast.error(errorInfo.message);
      console.error('Failed to load initial data:', error);
    }
  };

  // Handle village selection
  const handleVillageChange = async (villageName) => {
    setSelectedVillage(villageName);
    setVillageStructure(null);
    setComparisonResults(null);
    setChosenIndex('');
    
    if (villageName) {
      try {
        setIsLoading(true);
        const structureData = await apiService.getVillageStructure(villageName);
        setVillageStructure(structureData);
        toast.success(`Loaded ${villageName} structure`);
      } catch (error) {
        const errorInfo = handleApiError(error);
        toast.error(errorInfo.message);
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Run comparison
  const runComparison = async () => {
    if (!selectedVillage || chosenIndex === '') {
      toast.error('Please select a village and enter an index');
      return;
    }

    const indexNum = parseInt(chosenIndex);
    if (isNaN(indexNum) || indexNum < 0 || (villageStructure && indexNum >= villageStructure.num_features)) {
      toast.error(`Index must be between 0 and ${villageStructure?.num_features - 1 || 'N/A'}`);
      return;
    }

    try {
      setIsLoading(true);
      setComparisonResults(null);
      
      const results = await apiService.runComparison(selectedVillage, indexNum, comparisonMethod);
      setComparisonResults(results);
      setSessionId(results.session_id);
      
      if (results.best_match_found) {
        toast.success('Comparison completed successfully!');
      } else {
        toast.warning('Comparison completed but no good matches found');
      }
    } catch (error) {
      const errorInfo = handleApiError(error);
      toast.error(errorInfo.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Generate PDF report
  const generatePDF = async () => {
    if (!sessionId) {
      toast.error('No comparison session available');
      return;
    }

    try {
      setIsPdfGenerating(true);
      const pdfData = await apiService.generatePDF(sessionId);
      
      if (pdfData.success) {
        toast.success('PDF generated successfully!');
        // Automatically download the PDF
        await apiService.downloadPDF(pdfData.pdf_filename);
      }
    } catch (error) {
      const errorInfo = handleApiError(error);
      toast.error(errorInfo.message);
    } finally {
      setIsPdfGenerating(false);
    }
  };

  return (
    <motion.div
      className="p-6 bg-background min-h-screen"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* Header */}
      <motion.div
        className="mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h1 className="text-3xl font-bold text-text mb-2 flex items-center">
          <MdMap className="mr-3 text-primary" />
          Map Comparison Dashboard
        </h1>
        <p className="text-gray-600">Compare and analyze geographical plot data</p>
      </motion.div>

      {/* Backend Status */}
      <motion.div
        className="mb-6"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
      >
        <div className={`p-4 rounded-lg border-2 ${
          backendHealth?.success 
            ? 'bg-green-50 border-green-200 text-green-800'
            : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          <div className="flex items-center">
            {backendHealth?.success ? (
              <FaCheckCircle className="mr-2" />
            ) : (
              <FaExclamationTriangle className="mr-2" />
            )}
            <span className="font-semibold">
              Backend Status: {backendHealth?.success ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          {backendHealth?.dependencies && (
            <div className="mt-2 text-sm">
              <span>Dependencies: </span>
              <span className={backendHealth.dependencies.tensorflow ? 'text-green-600' : 'text-red-600'}>
                TensorFlow {backendHealth.dependencies.tensorflow ? '✓' : '✗'}
              </span>
              <span className="mx-2">|</span>
              <span className={backendHealth.dependencies.pillow ? 'text-green-600' : 'text-red-600'}>
                Pillow {backendHealth.dependencies.pillow ? '✓' : '✗'}
              </span>
              <span className="mx-2">|</span>
              <span className={backendHealth.dependencies.fpdf ? 'text-green-600' : 'text-red-600'}>
                PDF {backendHealth.dependencies.fpdf ? '✓' : '✗'}
              </span>
            </div>
          )}
        </div>
      </motion.div>

      {/* Configuration Panel */}
      <motion.div
        className="bg-cardBackground p-6 rounded-xl shadow-md border border-gray-200 mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <h2 className="text-xl font-semibold text-text mb-4 flex items-center">
          <MdCompare className="mr-2 text-primary" />
          Comparison Configuration
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Village Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Village
            </label>
            <select
              value={selectedVillage}
              onChange={(e) => handleVillageChange(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={isLoading}
            >
              <option value="">Choose a village...</option>
              {villages.map((village) => (
                <option key={village} value={village}>
                  {village.charAt(0).toUpperCase() + village.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Index Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Feature Index
              {villageStructure && (
                <span className="text-xs text-gray-500 ml-1">
                  (0-{villageStructure.num_features - 1})
                </span>
              )}
            </label>
            <input
              type="number"
              value={chosenIndex}
              onChange={(e) => setChosenIndex(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Enter index..."
              min="0"
              max={villageStructure?.num_features - 1 || undefined}
              disabled={!selectedVillage || isLoading}
            />
          </div>

          {/* Comparison Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Comparison Method
            </label>
            <select
              value={comparisonMethod}
              onChange={(e) => setComparisonMethod(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={isLoading}
            >
              <option value="standard">Standard (IoU + Hausdorff)</option>
              <option value="advanced" disabled={!backendHealth?.advanced_comparison_available}>
                Advanced (VGG16) {!backendHealth?.advanced_comparison_available && '- Unavailable'}
              </option>
            </select>
          </div>

          {/* Run Button */}
          <div className="flex items-end">
            <button
              onClick={runComparison}
              disabled={!selectedVillage || chosenIndex === '' || isLoading}
              className="w-full bg-primary text-white px-4 py-3 rounded-lg font-semibold hover:bg-activeButton transition duration-300 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? (
                <FaSpinner className="animate-spin mr-2" />
              ) : (
                <FaSearch className="mr-2" />
              )}
              {isLoading ? 'Running...' : 'Run Comparison'}
            </button>
          </div>
        </div>

        {/* Village Info */}
        {villageStructure && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h3 className="font-semibold text-blue-800 mb-2">Village Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium">Features:</span>
                <span className="ml-2">{villageStructure.num_features}</span>
              </div>
              <div>
                <span className="font-medium">Sub-villages:</span>
                <span className="ml-2">{villageStructure.sub_villages.length}</span>
              </div>
              <div>
                <span className="font-medium">Has Full Map:</span>
                <span className="ml-2">{villageStructure.has_full_map ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="font-medium">Sub-villages:</span>
                <span className="ml-2">{villageStructure.sub_villages.join(', ')}</span>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Results Panel */}
      {comparisonResults && (
        <motion.div
          className="bg-cardBackground p-6 rounded-xl shadow-md border border-gray-200"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-text flex items-center">
              <FaCheckCircle className="mr-2 text-green-600" />
              Comparison Results
            </h2>
            
            {comparisonResults.best_match_found && backendHealth?.pdf_generation_available && (
              <button
                onClick={generatePDF}
                disabled={isPdfGenerating}
                className="bg-secondary text-white px-4 py-2 rounded-lg font-semibold hover:bg-opacity-90 transition duration-300 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
              >
                {isPdfGenerating ? (
                  <FaSpinner className="animate-spin mr-2" />
                ) : (
                  <MdPictureAsPdf className="mr-2" />
                )}
                {isPdfGenerating ? 'Generating...' : 'Generate PDF'}
              </button>
            )}
          </div>

          {/* Best Match Info */}
          {comparisonResults.best_match_found && comparisonResults.best_match_info && (
            <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200">
              <h3 className="font-semibold text-green-800 mb-2">Best Match Found</h3>
              <div className="text-sm text-green-700">
                <div><strong>Filename:</strong> {comparisonResults.best_match_info.filename}</div>
                <div><strong>Score:</strong> {comparisonResults.best_match_info.score_info}</div>
              </div>
            </div>
          )}

          {/* Results Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Filename
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sub-village
                  </th>
                  {comparisonMethod === 'standard' ? (
                    <>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        IoU Score
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Hausdorff Distance
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Transform
                      </th>
                    </>
                  ) : (
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      VGG Similarity
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {comparisonResults.results.map((result, index) => (
                  <tr key={index} className={index === 0 ? 'bg-green-50' : 'hover:bg-gray-50'}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {index + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {result.filename || result.img_path?.split('/').pop()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {result.sub_village}
                    </td>
                    {comparisonMethod === 'standard' ? (
                      <>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {result.iou?.toFixed(3)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {result.hausdorff?.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {result.iou_transform}
                        </td>
                      </>
                    ) : (
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.similarity?.toFixed(3)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Session Info */}
          <div className="mt-4 text-xs text-gray-500">
            Session ID: {comparisonResults.session_id}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default MapComparisonDashboard;