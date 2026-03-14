import { useEffect, useRef } from "react";

export function useBodyScrollLock(isLocked: boolean): void {
  const previousOverflowRef = useRef<string>("");

  useEffect(() => {
    if (!isLocked) return;

    previousOverflowRef.current = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflowRef.current;
    };
  }, [isLocked]);
}
