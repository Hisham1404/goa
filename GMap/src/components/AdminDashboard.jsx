import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  FaUsers,
  FaMapMarkedAlt,
  FaClipboardList,
  FaCogs,
  FaUserShield,
  FaEdit,
  FaBookOpen,
} from "react-icons/fa";

const AdminDashboard = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [stats, setStats] = useState([]);
  const [sections, setSections] = useState([]);

  // Fetch data from users.json
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/users.json");
        const users = await response.json();

        // Calculate stats dynamically
        const totalUsers = users.length;
        const totalApplicationsProcessed = users
          .filter((u) => u.role === "general" && u.applicationStats)
          .reduce((sum, u) => sum + u.applicationStats[0].totalApplications, 0);
        const approvedApplications = users
          .filter((u) => u.role === "general" && u.applicationStats)
          .reduce(
            (sum, u) => sum + u.applicationStats[2].approvedApplications,
            0
          );
        const rejectedApplications =
          totalApplicationsProcessed - approvedApplications;

        setStats([
          {
            title: "Total Registered Users",
            value: totalUsers,
            color: "bg-blue-100 text-blue-600",
            icon: <FaUsers className="text-blue-600 text-4xl" />,
          },
          {
            title: "Total Applications Processed",
            value: totalApplicationsProcessed,
            color: "bg-green-100 text-green-600",
            icon: <FaEdit className="text-green-600 text-4xl" />,
          },
          {
            title: "Approved vs. Rejected",
            value: `${approvedApplications} / ${rejectedApplications}`,
            color: "bg-yellow-100 text-yellow-600",
            icon: <FaBookOpen className="text-yellow-600 text-4xl" />,
          },
        ]);

        // Set sections (static for now)
        setSections([
          {
            title: "Survey & Contour Management",
            content:
              "Update metadata and map contours for different locations.",
            icon: <FaMapMarkedAlt className="text-green-600 text-3xl" />,
          },
          {
            title: "Recent Activity Logs",
            content: "Track admin actions, approvals, and system changes.",
            icon: <FaClipboardList className="text-yellow-600 text-3xl" />,
          },
          {
            title: "System Configuration",
            content:
              "Modify settings, security policies, and database configurations.",
            icon: <FaCogs className="text-gray-600 text-3xl" />,
          },
        ]);
      } catch (err) {
        console.error("Error fetching data:", err);
      }
    };

    fetchData();
  }, []);

  const handleSearchUser = async () => {
    try {
      const response = await fetch("/users.json");
      const users = await response.json();
      const foundUser = users.find((u) => u.email === email);

      if (foundUser) {
        setUser(foundUser);
        setError("");
      } else {
        setUser(null);
        setError("User not found.");
      }
    } catch (err) {
      setError("An error occurred while fetching user data.");
    }
  };

  const handleRoleChange = (newRole) => {
    if (user) {
      setUser({ ...user, role: newRole });
      alert(`User role updated to ${newRole}`);
      setIsModalOpen(false);
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <motion.h2
        className="text-3xl font-bold text-gray-900 mb-6 flex items-center gap-2"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <FaUserShield className="text-blue-600" /> Welcome, Admin!
      </motion.h2>

      {/* Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((item, index) => (
          <motion.div
            key={index}
            className="bg-white p-6 shadow-md rounded-xl border border-gray-200 hover:shadow-lg transition flex items-center gap-4"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
          >
            {item.icon}
            <div>
              <h3 className="text-lg font-semibold text-gray-700 mb-1">
                {item.title}
              </h3>
              <p className={`text-2xl font-bold ${item.color} p-2 rounded-md`}>
                {item.value}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
        {sections.map((section, index) => (
          <motion.div
            key={index}
            className="bg-white p-6 shadow-md rounded-xl border border-gray-200 hover:shadow-lg transition flex items-start gap-4"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: index * 0.15 }}
          >
            {section.icon}
            <div>
              <h3 className="text-xl font-semibold text-gray-800">
                {section.title}
              </h3>
              <p className="text-gray-600">{section.content}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="mt-10 flex flex-wrap gap-4">
        <motion.button
          className="px-6 py-3 rounded-lg font-semibold shadow-md transition flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          onClick={() => setIsModalOpen(true)}
        >
          <FaUserShield /> Manage Users
        </motion.button>
      </div>

      {/* Modal for Managing Users */}
      {isModalOpen && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full relative">
            <button
              className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
              onClick={() => setIsModalOpen(false)}
            >
              &times;
            </button>
            <h3 className="text-xl font-bold mb-4">Manage User</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">
                Enter User Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border p-2 rounded mt-1"
              />
              <button
                onClick={handleSearchUser}
                className="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Search
              </button>
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            {user && (
              <div>
                <p className="text-gray-700">
                  User Found: <strong>{user.name}</strong>
                </p>
                <p className="text-gray-700">
                  Current Role: <strong>{user.role}</strong>
                </p>
                <div className="mt-4 flex gap-4">
                  <button
                    onClick={() => handleRoleChange("admin")}
                    className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                  >
                    Make Admin
                  </button>
                  <button
                    onClick={() => handleRoleChange("dslr")}
                    className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
                  >
                    Make DSLR
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
