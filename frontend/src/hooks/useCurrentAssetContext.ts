import { useLocation, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAsset } from "../api/assets.js";

/**
 * Ermittelt den aktuellen Asset-Kontext aus der URL.
 * Gültig auf /pipeline?assetId=xxx und /assets?assetId=xxx
 */
export function useCurrentAssetContext() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const assetId = searchParams.get("assetId");

  const isRelevantRoute =
    location.pathname === "/pipeline" || location.pathname === "/assets";

  const query = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => (assetId ? getAsset(assetId) : Promise.resolve(null)),
    enabled: !!assetId && isRelevantRoute,
  });

  return {
    assetId: assetId ?? null,
    asset: query.data ?? null,
    isLoading: query.isLoading,
  };
}
