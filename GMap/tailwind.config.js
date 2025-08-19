/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1E3A8A",
        secondary: "#3B82F6",
        accent: "#10B981",
        danger: "#EF4444",
        background: "#F3F4F6",
        sidebarText: "#FFFFFF",
        text: "#1F2937",
        cardBackground: "#FFFFFF",
        hoverSidebar: "#374151",
        activeButton: "#2563EB",
      },
    },
  },
  plugins: [],
};
