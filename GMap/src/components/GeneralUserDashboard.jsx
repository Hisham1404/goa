import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { FaCheckCircle, FaTimesCircle } from "react-icons/fa";
import { MdOutlineSummarize } from "react-icons/md";
import { MdOutlineClose } from "react-icons/md";
import { AiOutlineClockCircle } from "react-icons/ai";
import { HiOutlineDocumentAdd } from "react-icons/hi";
import CustomForm from "./CustomForm";

const GeneralUserDashboard = () => {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [userName, setUserName] = useState("");
  const [applicationStats, setApplicationStats] = useState([]);
  const [recentApplications, setRecentApplications] = useState([]);
  const [notifications, setNotifications] = useState([]);

  const loadApplications = () => {
    const applications = JSON.parse(localStorage.getItem('mapApplications') || '[]');
    setRecentApplications(applications);
    
    // Update statistics based on applications
    const totalApps = applications.length;
    const pendingApps = applications.filter(app => app.status === 'Pending DSLR Approval').length;
    const approvedApps = applications.filter(app => app.status === 'Approved' || app.status === 'Ready for Download').length;
    
    setApplicationStats([
      {
        title: "Total Applications Submitted",
        value: totalApps.toString(),
        color: "bg-blue-100 text-blue-600",
        icon: <MdOutlineSummarize className="text-blue-600 text-3xl" />,
      },
      {
        title: "Pending Applications",
        value: pendingApps.toString(),
        color: "bg-yellow-100 text-yellow-600",
        icon: (
          <AiOutlineClockCircle className="text-yellow-500 text-2xl" />
        ),
      },
      {
        title: "Approved Applications",
        value: approvedApps.toString(),
        color: "bg-green-100 text-green-600",
        icon: <FaCheckCircle className="text-green-600 text-2xl" />,
      },
    ]);
  };

  const handleDownloadPDF = async (application) => {
    try {
      // First, generate the PDF
      const pdfResponse = await fetch(`http://localhost:5000/api/generate-pdf/${application.sessionId}`, {
        method: 'POST'
      });
      
      const pdfData = await pdfResponse.json();
      
      if (pdfData.success) {
        // Then download the generated PDF
        const downloadResponse = await fetch(`http://localhost:5000/api/download-pdf/${pdfData.pdf_filename}`);
        
        if (downloadResponse.ok) {
          const blob = await downloadResponse.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = `map_comparison_report_${application.id}.pdf`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        } else {
          alert('Failed to download PDF. Please try again.');
        }
      } else {
        alert('Failed to generate PDF. Please try again.');
      }
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Error downloading PDF. Please try again.');
    }
  };

  // Fetch data from users.json
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/users.json");
        const users = await response.json();

        // Find the general user
        const generalUser = users.find((user) => user.role === "general");

        if (generalUser) {
          setUserName(generalUser.name);
          setNotifications(generalUser.notifications);
        }
      } catch (err) {
        console.error("Error fetching data:", err);
      }
    };

    fetchData();
    // Load applications from localStorage
    loadApplications();
  }, []);

  // Reload applications when modal closes
  useEffect(() => {
    if (!isModalOpen) {
      loadApplications();
    }
  }, [isModalOpen]);

  return (
    <motion.div
      className="p-6 bg-background min-h-screen"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* Welcome Message */}
      <motion.h2
        className="text-3xl font-bold text-text mb-6"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        Welcome, {userName}!
      </motion.h2>



      {/* Application Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {applicationStats.map((item, index) => (
          <motion.div
            key={index}
            className={`p-6 shadow-md rounded-xl border-2 ${item.color} hover:shadow-lg transition transform`}
            initial={{ opacity: 0, y: -0 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            whileHover={{ scale: 1.05 }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{item.title}</h3>
              {item.icon}
            </div>
            <p className="mt-4 text-3xl font-bold">{item.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Apply for New Certificate Button */}
      <div className="mt-4 flex justify-end">
        <motion.button
          className="bg-primary text-sidebarText px-6 py-3 rounded-lg font-semibold shadow-md hover:bg-activeButton transition duration-300 ease-in-out hover:scale-105 flex items-center"
          whileHover={{ scale: 1.05 }}
          initial={{ opacity: 0, y: -0 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          onClick={() => setIsModalOpen(true)}
        >
          <HiOutlineDocumentAdd className="text-2xl mr-2" />
          Submit New Application
        </motion.button>
      </div>

      {/* Application Status & Tracking */}
      <motion.div
        className="mt-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <h3 className="text-xl font-semibold text-text mb-4">
          Recent Application Status
        </h3>
        <div className="bg-cardBackground p-4 shadow-md rounded-xl border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Application ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Submission Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Current Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recentApplications.length > 0 ? recentApplications.map((application) => (
                <motion.tr
                  key={application.id}
                  whileHover={{ backgroundColor: "#f3f4f6" }}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    {application.id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {application.submissionDate}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        application.status === "Pending DSLR Approval" ? "bg-yellow-100 text-yellow-800" :
                        application.status === "Approved" ? "bg-green-100 text-green-800" :
                        application.status === "Ready for Download" ? "bg-blue-100 text-blue-800" :
                        application.status === "Rejected" ? "bg-red-100 text-red-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {application.status}
                      </span>
                      {application.status === "Pending DSLR Approval" && (
                        <AiOutlineClockCircle className="text-yellow-500 text-xl ml-2" />
                      )}
                      {(application.status === "Approved" || application.status === "Ready for Download") && (
                        <FaCheckCircle className="text-green-600 text-xl ml-2" />
                      )}
                      {application.status === "Rejected" && (
                        <FaTimesCircle className="text-red-600 text-xl ml-2" />
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button 
                      className="bg-secondary text-sidebarText px-3 py-1 rounded mr-2 hover:bg-blue-600 transition"
                      onClick={() => {
                        alert(`Application Details:\n\nID: ${application.id}\nType: ${application.type}\nDirection: ${application.direction}\nVillage: ${application.village}\nSurvey Number: ${application.surveyNumber || 'N/A'}\nStatus: ${application.status}\nSubmission Date: ${application.submissionDate}`);
                      }}
                    >
                      View Details
                    </button>
                    {application.status === "Rejected" && (
                      <button className="bg-primary text-sidebarText px-3 py-1 rounded hover:bg-green-600 transition">
                        Reapply
                      </button>
                    )}
                    {application.status === "Ready for Download" && (
                      <button 
                        className="bg-green-500 text-white px-3 py-1 rounded hover:bg-green-600 transition"
                        onClick={() => handleDownloadPDF(application)}
                      >
                        Download PDF
                      </button>
                    )}
                  </td>
                </motion.tr>
              )) : (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                    No applications submitted yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Notifications & Updates */}
      <motion.div
        className="mt-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <h3 className="text-xl font-semibold text-text mb-4">
          Notifications & Updates
        </h3>
        <div className="bg-cardBackground p-4 shadow-md rounded-xl border border-gray-200">
          {notifications.length > 0 ? (
            <ul className="space-y-4">
              {notifications.map((notification, index) => (
                <motion.li
                  key={index}
                  className={`flex items-center p-4 rounded-lg shadow-md ${
                    notification.type === "success"
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}
                  whileHover={{ scale: 1.02 }}
                >
                  {notification.type === "success" ? (
                    <FaCheckCircle className="text-green-600 text-2xl mr-4" />
                  ) : (
                    <FaTimesCircle className="text-red-600 text-2xl mr-4" />
                  )}
                  <span>{notification.message}</span>
                </motion.li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-center">No new notifications</p>
          )}
        </div>
      </motion.div>

      {isModalOpen && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <motion.div
            initial={{ opacity: 1, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            duration={0.5}
            exit={{ opacity: 0, scale: 0 }}
            transition={{ delay: 0 }}
            className="bg-white p-6 rounded-lg  max-w-md w-full"
          >
            <button
              className=" relative  flex w-full justify-end   text-black hover:text-gray-700"
              onClick={() => setIsModalOpen(false)}
            >
              <div className="absolute flex    text-3xl text-black hover:text-gray-700">
                <MdOutlineClose />
              </div>
            </button>
            <CustomForm />
          </motion.div>
        </div>
      )}
    </motion.div>
  );
};

export default GeneralUserDashboard;
