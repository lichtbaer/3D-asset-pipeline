import axios from "axios";

/** Server base URL without API version prefix (for static files). */
export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_URL = `${API_BASE}/api/v1`;
const API_KEY = import.meta.env.VITE_API_KEY;

const headers: Record<string, string> = {
  "Content-Type": "application/json",
};
if (API_KEY) {
  headers["Authorization"] = `Bearer ${API_KEY}`;
}

export const apiClient = axios.create({
  baseURL: API_URL,
  headers,
});
