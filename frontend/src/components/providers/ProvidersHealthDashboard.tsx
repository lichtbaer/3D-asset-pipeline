/**
 * ProvidersHealthDashboard – Übersicht über alle Provider-Status.
 *
 * Zeigt gruppierten Status für Image, Mesh, BgRemoval, Rigging und Animation Provider.
 */

import { useQuery } from "@tanstack/react-query";
import "./ProvidersHealth.css";
import { getProvidersHealth, type ProviderHealthInfo } from "../../api/providers.js";
import { ProviderHealthBadge } from "./ProviderHealthBadge.js";

const TYPE_LABELS: Record<string, string> = {
  image: "Bildgenerierung",
  mesh: "Mesh-Generierung",
  bgremoval: "Background-Removal",
  rigging: "Rigging",
  animation: "Animation",
};

const TYPE_ORDER = ["image", "mesh", "bgremoval", "rigging", "animation"];

function ProviderRow({ provider }: { provider: ProviderHealthInfo }) {
  return (
    <tr className="providers-health__row">
      <td className="providers-health__cell providers-health__cell--name">
        {provider.display_name}
        <code className="providers-health__key"> ({provider.key})</code>
      </td>
      <td className="providers-health__cell providers-health__cell--status">
        <ProviderHealthBadge
          status={provider.status}
          reason={provider.reason}
          size="lg"
        />
      </td>
      <td className="providers-health__cell providers-health__cell--reason">
        {provider.reason && (
          <span className="providers-health__reason">{provider.reason}</span>
        )}
      </td>
    </tr>
  );
}

export function ProvidersHealthDashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["providers-health"],
    queryFn: getProvidersHealth,
    refetchInterval: 60_000,    // Alle 60 Sekunden neu laden
    staleTime: 55_000,
  });

  if (isLoading) {
    return (
      <div className="providers-health providers-health--loading">
        <p>Lade Provider-Status...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="providers-health providers-health--error">
        <p>Provider-Status konnte nicht geladen werden.</p>
      </div>
    );
  }

  // Gruppiere nach provider_type in definierter Reihenfolge
  const byType = new Map<string, ProviderHealthInfo[]>();
  for (const type of TYPE_ORDER) {
    byType.set(type, []);
  }
  for (const p of data.providers) {
    const list = byType.get(p.provider_type) ?? [];
    list.push(p);
    byType.set(p.provider_type, list);
  }

  const checkedAt = new Date(data.checked_at * 1000).toLocaleTimeString("de-DE");

  return (
    <div className="providers-health">
      <div className="providers-health__header">
        <h2 className="providers-health__title">Provider-Status</h2>
        <span className="providers-health__meta">
          {data.cached ? "gecacht · " : ""}
          geprüft um {checkedAt}
        </span>
      </div>

      {TYPE_ORDER.map((type) => {
        const providers = byType.get(type) ?? [];
        if (providers.length === 0) return null;

        const anyUnavailable = providers.some((p) => p.status === "unavailable");
        const anyDegraded = providers.some((p) => p.status === "degraded");
        const groupStatus = anyUnavailable
          ? "unavailable"
          : anyDegraded
          ? "degraded"
          : "healthy";

        return (
          <section key={type} className="providers-health__group">
            <h3 className="providers-health__group-title">
              {TYPE_LABELS[type] ?? type}
              <ProviderHealthBadge status={groupStatus} size="sm" />
            </h3>
            <table className="providers-health__table">
              <thead>
                <tr>
                  <th className="providers-health__th">Provider</th>
                  <th className="providers-health__th">Status</th>
                  <th className="providers-health__th">Hinweis</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => (
                  <ProviderRow key={p.key} provider={p} />
                ))}
              </tbody>
            </table>
          </section>
        );
      })}
    </div>
  );
}
