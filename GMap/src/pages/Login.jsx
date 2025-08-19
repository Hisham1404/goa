import React, { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import { useNavigate } from "react-router-dom";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Fetch users from the JSON file
      const response = await fetch("/users.json");
      const users = await response.json();
      console.log(users);

      // Check if the user exists
      const user = users.find(
        (u) => u.email === email && u.password === password
      );

      if (user) {
        setError("");
        toast.success("Login successful!");
        localStorage.setItem("loggedInUser", JSON.stringify(user));

        // Redirect based on user role
        if (user.role === "admin") {
          navigate("/admin");
        } else if (user.role === "general") {
          navigate("/general");
        } else if (user.role === "dslr") {
          navigate("/dslr");
        }

        setEmail("");
        setPassword("");
      } else {
        setError("Invalid credentials. Please try again.");
        toast.error("Invalid credentials.");
      }
    } catch (err) {
      setError("An error occurred while logging in. Please try again.");
      toast.error("An error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full h-screen flex items-center justify-center bg-gray-100 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-72 h-72 bg-blue-500 rounded-full opacity-20 blur-3xl"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500 rounded-full opacity-20 blur-3xl"></div>

      {/* Login Form */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="bg-white w-full max-w-md p-8 rounded-lg shadow-lg z-10"
      >
        <h2 className="text-2xl font-bold text-center text-gray-800">
          Sign In
        </h2>
        <p className="mt-2 text-sm text-center text-gray-600">
          Log in to access your account
        </p>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-4 px-4 py-2 text-sm text-red-700 bg-red-100 border border-red-400 rounded"
          >
            {error}
          </motion.div>
        )}

        <form className="mt-6 space-y-6" onSubmit={handleLogin}>
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700"
            >
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-1 py-1 mt-1 text-gray-800 border-b-2 border-gray-300 outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-1 py-1 mt-1 text-gray-800 border-b-2 border-gray-300 outline-none focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className={`w-full px-4 py-2 text-white rounded-lg shadow-md transition-colors ${
              isLoading ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"
            } focus:outline-none focus:ring-2 focus:ring-blue-500`}
          >
            {isLoading ? "Logging in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-sm text-center text-gray-600">
          New here?{" "}
          <button
            onClick={() => navigate("/register")}
            className="text-blue-600 hover:underline"
          >
            Register
          </button>
        </p>
      </motion.div>
    </div>
  );
}

export default Login;
