import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FiCheckCircle, FiXCircle, FiSearch, FiX, FiDownload } from "react-icons/fi";
import toast from "react-hot-toast";

const DslrOfficerDashboard = () => {
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState([]);
  const [recentActivityLogs, setRecentActivityLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [comparisonResults, setComparisonResults] = useState({ standard: null, advanced: null });
  const [loadingComparison, setLoadingComparison] = useState({ standard: false, advanced: false });
  const [selectedMethod, setSelectedMethod] = useState(null);

  const loadApplications = () => {
    const allApplications = JSON.parse(localStorage.getItem('mapApplications') || '[]');
    setApplications(allApplications);
    
    // Calculate statistics
    const totalApps = allApplications.length;
    const pendingApps = allApplications.filter(app => app.status === 'Pending DSLR Approval').length;
    const approvedApps = allApplications.filter(app => app.status === 'Approved' || app.status === 'Ready for Download').length;
    const rejectedApps = allApplications.filter(app => app.status === 'Rejected').length;
    
    setStats([
      {
        title: "Total Applications Received",
        value: totalApps.toString(),
        color: "bg-blue-100 text-blue-600",
      },
      {
        title: "Pending Applications",
        value: pendingApps.toString(),
        color: "bg-yellow-100 text-yellow-600",
      },
      {
        title: "Approved Applications",
        value: approvedApps.toString(),
        color: "bg-green-100 text-green-600",
      },
      {
        title: "Rejected Applications",
        value: rejectedApps.toString(),
        color: "bg-red-100 text-red-600",
      },
    ]);
    
    // Load activity logs from localStorage
    const logs = JSON.parse(localStorage.getItem('activityLogs') || '[]');
    setRecentActivityLogs(logs.slice(-5)); // Show last 5 activities
  };

  const handleApprove = (applicationId) => {
    const updatedApplications = applications.map(app => {
      if (app.id === applicationId) {
        return { ...app, status: 'Ready for Download' };
      }
      return app;
    });
    
    localStorage.setItem('mapApplications', JSON.stringify(updatedApplications));
    
    // Add to activity logs
    const logs = JSON.parse(localStorage.getItem('activityLogs') || '[]');
    const newLog = `${new Date().toISOString().split('T')[0]}: Approved application ID ${applicationId}`;
    logs.push(newLog);
    localStorage.setItem('activityLogs', JSON.stringify(logs));
    
    loadApplications();
    toast.success(`Application ${applicationId} approved successfully!`);
  };

  const handleReject = (applicationId) => {
    const updatedApplications = applications.map(app => {
      if (app.id === applicationId) {
        return { ...app, status: 'Rejected' };
      }
      return app;
    });
    
    localStorage.setItem('mapApplications', JSON.stringify(updatedApplications));
    
    // Add to activity logs
    const logs = JSON.parse(localStorage.getItem('activityLogs') || '[]');
    const newLog = `${new Date().toISOString().split('T')[0]}: Rejected application ID ${applicationId}`;
    logs.push(newLog);
    localStorage.setItem('activityLogs', JSON.stringify(logs));
    
    loadApplications();
    toast.error(`Application ${applicationId} rejected.`);
  };

  const runComparison = async (method) => {
    if (!selectedApplication || !selectedApplication.surveyNumber) {
      toast.error('Survey number is required for comparison');
      return;
    }

    setLoadingComparison(prev => ({ ...prev, [method]: true }));
    
    try {
      const response = await fetch('http://localhost:5000/api/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          village_name: selectedApplication.village,
          chosen_index: parseInt(selectedApplication.surveyNumber),
          comparison_method: method
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setComparisonResults(prev => ({ ...prev, [method]: data }));
        toast.success(`${method.charAt(0).toUpperCase() + method.slice(1)} comparison completed!`);
      } else {
        toast.error(`${method.charAt(0).toUpperCase() + method.slice(1)} comparison failed: ${data.error}`);
      }
    } catch (error) {
      console.error(`${method} comparison error:`, error);
      toast.error(`${method.charAt(0).toUpperCase() + method.slice(1)} comparison failed`);
    } finally {
      setLoadingComparison(prev => ({ ...prev, [method]: false }));
    }
  };

  const handleViewDetails = (application) => {
    setSelectedApplication(application);
    setShowComparisonModal(true);
    setComparisonResults({ standard: null, advanced: null });
    setSelectedMethod(null);
  };

  const handleDownloadPreview = async (method) => {
    const selectedResult = comparisonResults[method];
    
    if (selectedResult && selectedResult.session_id) {
      try {
        // Generate PDF for preview
        const pdfResponse = await fetch(`http://localhost:5000/api/generate-pdf/${selectedResult.session_id}`, {
          method: 'POST'
        });
        
        const pdfData = await pdfResponse.json();
        
        if (pdfData.success) {
          // Download the PDF for review
          const downloadResponse = await fetch(`http://localhost:5000/api/download-pdf/${pdfData.pdf_filename}`);
          
          if (downloadResponse.ok) {
            const blob = await downloadResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `preview_${method}_${selectedApplication.id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            toast.success(`${method.charAt(0).toUpperCase() + method.slice(1)} PDF downloaded for review!`);
            setSelectedMethod(method);
          } else {
            toast.error('Failed to download PDF preview');
          }
        } else {
          toast.error('Failed to generate PDF preview');
        }
      } catch (error) {
        console.error('PDF preview error:', error);
        toast.error('Failed to download PDF preview');
      }
    }
  };

  const handleApproveMethod = async (method) => {
    const selectedResult = comparisonResults[method];
    
    if (selectedResult && selectedResult.session_id) {
      try {
        // Update application status and add PDF info
        const updatedApplications = applications.map(app => {
          if (app.id === selectedApplication.id) {
            return { 
              ...app, 
              status: 'Ready for Download',
              comparisonMethod: method,
              sessionId: selectedResult.session_id
            };
          }
          return app;
        });
        
        localStorage.setItem('mapApplications', JSON.stringify(updatedApplications));
        
        // Add to activity logs
        const logs = JSON.parse(localStorage.getItem('activityLogs') || '[]');
        const newLog = `${new Date().toISOString().split('T')[0]}: Approved application ID ${selectedApplication.id} with ${method} method`;
        logs.push(newLog);
        localStorage.setItem('activityLogs', JSON.stringify(logs));
        
        loadApplications();
        setShowComparisonModal(false);
        toast.success(`Application approved with ${method} method!`);
      } catch (error) {
        console.error('Approval error:', error);
        toast.error('Failed to approve application');
      }
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  // Filter applications based on search and status
  const filteredApplications = applications.filter(app => {
    const matchesSearch = app.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         app.village.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (app.surveyNumber && app.surveyNumber.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = statusFilter === 'all' || app.status.toLowerCase().includes(statusFilter.toLowerCase());
    return matchesSearch && matchesStatus;
  });

  const pendingApplications = filteredApplications.filter(app => app.status === 'Pending DSLR Approval');

  return (
    <div className="p-6 bg-background min-h-screen flex flex-col gap-6">
      <motion.h2
        className="text-3xl font-bold text-text"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        Welcome, Officer [User Name]!
      </motion.h2>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {stats.map((item, index) => (
          <motion.div
            key={index}
            className="bg-cardBackground p-6 shadow-lg rounded-xl border border-gray-200 hover:shadow-2xl transition"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
          >
            <h3 className="text-lg font-semibold text-text mb-2">
              {item.title}
            </h3>
            <p className={`text-2xl font-bold ${item.color} p-2 rounded-md`}>
              {item.value}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Pending Applications */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <h3 className="text-xl font-semibold text-text mb-4">
          Pending Applications
        </h3>
        <div className="bg-cardBackground p-4 shadow-md rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-gray-500">Application ID</th>
                <th className="px-6 py-3 text-gray-500">Type</th>
                <th className="px-6 py-3 text-gray-500">Village</th>
                <th className="px-6 py-3 text-gray-500">Direction</th>
                <th className="px-6 py-3 text-gray-500">Submission Date</th>
                <th className="px-6 py-3 text-gray-500">Status</th>
                <th className="px-6 py-3 text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pendingApplications.length > 0 ? pendingApplications.map((application) => (
                <tr key={application.id}>
                  <td className="px-6 py-4">{application.id}</td>
                  <td className="px-6 py-4">{application.type}</td>
                  <td className="px-6 py-4">{application.village}</td>
                  <td className="px-6 py-4">{application.direction}</td>
                  <td className="px-6 py-4">{application.submissionDate}</td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      {application.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <motion.button
                        className="bg-green-500 text-white px-3 py-1 rounded mr-2 flex items-center gap-1"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleApprove(application.id)}
                      >
                        <FiCheckCircle /> Approve
                      </motion.button>
                      <motion.button
                        className="bg-red-500 text-white px-3 py-1 rounded mr-2 flex items-center gap-1"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleReject(application.id)}
                      >
                        <FiXCircle /> Reject
                      </motion.button>
                      <motion.button
                        className="bg-blue-500 text-white px-3 py-1 rounded flex items-center gap-1"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleViewDetails(application)}
                      >
                        View Details
                      </motion.button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" className="px-6 py-4 text-center text-gray-500">
                    No pending applications
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Search & Filtering Options */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3 }}
      >
        <h3 className="text-xl font-semibold text-text mb-4">
          Search & Filtering Options
        </h3>
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="Search by Application ID, Village, or Survey Number"
            className="border p-2 rounded flex-1"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <motion.button
            className="bg-primary text-sidebarText p-2 rounded flex items-center gap-1"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => loadApplications()}
          >
            <FiSearch /> Refresh
          </motion.button>
        </div>
        <div className="mt-4">
          <select 
            className="border p-2 rounded"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </motion.div>

      {/* Recent Activity Logs */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <h3 className="text-xl font-semibold text-text mb-4">
          Recent Activity Logs
        </h3>
        <div className="bg-cardBackground p-4 shadow-md rounded-xl border border-gray-200">
          {recentActivityLogs.length > 0 ? (
            <ul className="list-disc pl-5 space-y-2">
              {recentActivityLogs.map((log, index) => (
                <li key={index} className="text-gray-700">{log}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-center">No recent activity</p>
          )}
        </div>
      </motion.div>

      {/* Comparison Modal */}
      {showComparisonModal && selectedApplication && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800">
                Application Details & Comparison
              </h2>
              <button
                onClick={() => setShowComparisonModal(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <FiX size={24} />
              </button>
            </div>

            {/* Application Details */}
            <div className="bg-gray-50 p-4 rounded-lg mb-6">
              <h3 className="text-lg font-semibold mb-3">Application Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div><strong>ID:</strong> {selectedApplication.id}</div>
                <div><strong>Type:</strong> {selectedApplication.type}</div>
                <div><strong>Village:</strong> {selectedApplication.village}</div>
                <div><strong>Direction:</strong> {selectedApplication.direction}</div>
                <div><strong>Survey Number:</strong> {selectedApplication.surveyNumber || 'N/A'}</div>
                <div><strong>Submission Date:</strong> {selectedApplication.submissionDate}</div>
              </div>
            </div>

            {/* Comparison Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {/* Standard Comparison */}
              <div className="border rounded-lg p-4">
                <h4 className="text-lg font-semibold mb-3">Standard Comparison</h4>
                <p className="text-gray-600 mb-4">Uses IoU and Hausdorff distance metrics for basic similarity analysis.</p>
                
                <button
                  onClick={() => runComparison('standard')}
                  disabled={loadingComparison.standard}
                  className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 disabled:opacity-50 mb-3"
                >
                  {loadingComparison.standard ? 'Running...' : 'Run Standard Comparison'}
                </button>

                {comparisonResults.standard && (
                  <div className="bg-green-50 p-3 rounded">
                    <p className="text-sm text-green-800 mb-2">✓ Comparison completed</p>
                    <p className="text-xs text-gray-600">Session ID: {comparisonResults.standard.session_id}</p>
                    <p className="text-xs text-gray-600">Matches found: {comparisonResults.standard.results?.length || 0}</p>
                    <button
                      onClick={() => handleDownloadPreview('standard')}
                      className="w-full mt-2 bg-blue-600 text-white py-1 px-3 rounded text-sm hover:bg-blue-700"
                    >
                      Download PDF Preview
                    </button>
                  </div>
                )}
              </div>

              {/* Advanced Comparison */}
              <div className="border rounded-lg p-4">
                <h4 className="text-lg font-semibold mb-3">Advanced Comparison</h4>
                <p className="text-gray-600 mb-4">Uses VGG16 neural network for deep feature analysis and similarity.</p>
                
                <button
                  onClick={() => runComparison('advanced')}
                  disabled={loadingComparison.advanced}
                  className="w-full bg-purple-500 text-white py-2 px-4 rounded hover:bg-purple-600 disabled:opacity-50 mb-3"
                >
                  {loadingComparison.advanced ? 'Running...' : 'Run Advanced Comparison'}
                </button>

                {comparisonResults.advanced && (
                  <div className="bg-green-50 p-3 rounded">
                    <p className="text-sm text-green-800 mb-2">✓ Comparison completed</p>
                    <p className="text-xs text-gray-600">Session ID: {comparisonResults.advanced.session_id}</p>
                    <p className="text-xs text-gray-600">Matches found: {comparisonResults.advanced.results?.length || 0}</p>
                    <button
                      onClick={() => handleDownloadPreview('advanced')}
                      className="w-full mt-2 bg-purple-600 text-white py-1 px-3 rounded text-sm hover:bg-purple-700"
                    >
                      Download PDF Preview
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Method Selection */}
            {(comparisonResults.standard || comparisonResults.advanced) && (
              <div className="border-t pt-6">
                <h4 className="text-lg font-semibold mb-4">Review PDFs and Approve Best Method</h4>
                <p className="text-sm text-gray-600 mb-4">Download and review the PDF reports above, then approve the method that provides the best results.</p>
                <div className="flex gap-4">
                  {comparisonResults.standard && (
                    <button
                      onClick={() => handleApproveMethod('standard')}
                      className={`px-6 py-3 rounded-lg border-2 transition-all ${
                        selectedMethod === 'standard'
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 hover:border-blue-300'
                      }`}
                    >
                      <FiDownload className="inline mr-2" />
                      Approve Standard Method
                    </button>
                  )}
                  {comparisonResults.advanced && (
                    <button
                      onClick={() => handleApproveMethod('advanced')}
                      className={`px-6 py-3 rounded-lg border-2 transition-all ${
                        selectedMethod === 'advanced'
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-300 hover:border-purple-300'
                      }`}
                    >
                      <FiDownload className="inline mr-2" />
                      Approve Advanced Method
                    </button>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-3">
                  Selecting a method will approve the application and generate a PDF report for the user to download.
                </p>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default DslrOfficerDashboard;
