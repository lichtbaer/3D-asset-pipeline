import type { ReactNode } from "react";

export interface TooltipProps {
  text: string;
  children: ReactNode;
  position?: "top" | "bottom";
}

export function Tooltip({ text, children, position = "top" }: TooltipProps) {
  return (
    <span
      className={`tooltip-wrapper tooltip-wrapper--${position}`}
      data-tooltip={text}
    >
      {children}
    </span>
  );
}
