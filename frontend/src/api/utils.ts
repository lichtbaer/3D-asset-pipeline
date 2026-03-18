import { API_BASE, apiClient } from "./client.js";

/**
 * Convert a potentially relative URL to an absolute URL using the API base.
 * If the URL is already absolute (starts with "http"), it is returned as-is.
 * Returns null if the input is null/undefined.
 */
export function toAbsoluteUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

/**
 * Create a typed retry function for a job endpoint.
 * Returns a function that posts to the retry endpoint and normalises the response.
 */
export function createRetryFn(
  basePath: string
): (jobId: string) => Promise<{ job_id: string; status: string }> {
  return async (jobId: string) => {
    const { data } = await apiClient.post<{ job_id: string; status: string }>(
      `${basePath}/retry/${jobId}`
    );
    return { job_id: String(data.job_id), status: data.status };
  };
}
