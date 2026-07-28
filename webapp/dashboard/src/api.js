// api.js
// Central place for the backend API base URL.
// - When deployed (e.g. on Vercel), set VITE_API_URL as an environment variable
//   to your deployed backend's URL (e.g. https://your-app.onrender.com).
// - When running locally with `npm run dev`, it falls back to localhost
//   automatically if VITE_API_URL is not set.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';
