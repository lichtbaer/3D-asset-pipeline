import { useState, useEffect } from "react";

interface ElapsedTimeProps {
  startTime: string; // ISO date string
}

export function ElapsedTime({ startTime }: ElapsedTimeProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(startTime).getTime();
    const update = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [startTime]);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  return (
    <span className="elapsed-time">
      {minutes}:{String(seconds).padStart(2, "0")}
    </span>
  );
}
