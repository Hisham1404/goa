import { FiUser, FiCheckCircle, FiSettings, FiFileText } from "react-icons/fi";

const Sidebar = ({ role, setActivePage }) => {
  const menuItems = {
    general: [
      { name: "Dashboard", icon: <FiUser />, page: "dashboard" },
      { name: "Applications", icon: <FiFileText />, page: "applications" },
    ],
    dslr: [
      { name: "Approval Queue", icon: <FiCheckCircle />, page: "approval" },
      { name: "Search", icon: <FiFileText />, page: "search" },
    ],
    admin: [
      { name: "User Management", icon: <FiUser />, page: "user_management" },
      { name: "Survey & Contours", icon: <FiSettings />, page: "survey" },
    ],
  };

  return (
    <div className="w-64 bg-primary text-sidebarText h-screen p-4">
      <h2 className="text-xl font-bold mb-4">Dashboard</h2>
      {menuItems[role].map((item) => (
        <button
          key={item.page}
          onClick={() => setActivePage(item.page)}
          className="flex items-center gap-2 p-2 w-full hover:bg-hoverSidebar rounded"
        >
          {item.icon} {item.name}
        </button>
      ))}
    </div>
  );
};

export default Sidebar;
