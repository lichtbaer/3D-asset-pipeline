/**
 * Extract a human-readable error message from an unknown error value.
 * Handles Axios error responses, plain Error instances, and fallback strings.
 */
export function extractErrorMessage(
  error: unknown,
  fallback = "Ein unbekannter Fehler ist aufgetreten."
): string {
  if (error && typeof error === "object" && "response" in error) {
    const res = (error as { response?: { data?: { detail?: unknown; message?: unknown } } })
      .response?.data;
    if (res) {
      if (typeof res.detail === "string") return res.detail;
      if (
        res.detail &&
        typeof res.detail === "object" &&
        "message" in (res.detail as Record<string, unknown>)
      ) {
        return String((res.detail as { message: unknown }).message);
      }
      if (typeof res.message === "string") return res.message;
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
