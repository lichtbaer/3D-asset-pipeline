/**
 * ProviderHealthBadge – zeigt den Gesundheitsstatus eines Providers als farbiges Badge.
 */

import type { ProviderStatus } from "../../api/providers.js";

interface ProviderHealthBadgeProps {
  status: ProviderStatus;
  reason?: string | null;
  /** Größe: 'sm' (default) oder 'lg' */
  size?: "sm" | "lg";
}

const STATUS_LABELS: Record<ProviderStatus, string> = {
  healthy: "Verfügbar",
  degraded: "Eingeschränkt",
  unavailable: "Nicht verfügbar",
};

export function ProviderHealthBadge({
  status,
  reason,
  size = "sm",
}: ProviderHealthBadgeProps) {
  const label = STATUS_LABELS[status];

  return (
    <span
      className={`provider-health-badge provider-health-badge--${status} provider-health-badge--${size}`}
      title={reason ?? label}
      aria-label={`Provider-Status: ${label}${reason ? ` (${reason})` : ""}`}
    >
      <span
        className="provider-health-badge__dot"
        aria-hidden="true"
      />
      {size === "lg" && (
        <span className="provider-health-badge__label">{label}</span>
      )}
    </span>
  );
}
