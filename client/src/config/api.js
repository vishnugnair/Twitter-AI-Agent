// API Configuration
const API_BASE_URL =
  import.meta.env.VITE_REACT_APP_API_BASE_URL ||
  process.env.REACT_APP_API_BASE_URL ||
  "https://twitter-growth-agent.onrender.com";

export { API_BASE_URL };
