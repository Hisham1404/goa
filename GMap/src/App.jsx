import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import GeneralUserDashboard from "./components/GeneralUserDashboard";
import DslrOfficerDashboard from "./components/DslrOfficerDashboard ";
import AdminDashboard from "./components/AdminDashboard";
import CustomForm from "./components/CustomForm";
import MapComparisonDashboard from "./components/MapComparisonDashboard";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/general" element={<GeneralUserDashboard />} />
        <Route path="/dslr" element={<DslrOfficerDashboard />} />
        <Route path="/form" element={<CustomForm />} />
        <Route path="/map-comparison" element={<MapComparisonDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
