import { useEffect } from "react";

export function useEscapeKey(
  handler: () => void,
  isActive: boolean = true
): void {
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handler();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handler, isActive]);
}
