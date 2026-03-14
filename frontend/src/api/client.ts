import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
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
