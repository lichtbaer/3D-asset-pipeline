import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAsset } from "../api/assets.js";

/**
 * Liest assetId aus URL-Param und lädt das Asset.
 * Für Pipeline-Tabs: rigging, animation, mesh-processing
 */
export function useAssetFromUrl() {
  const [searchParams] = useSearchParams();
  const assetId = searchParams.get("assetId");

  const query = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => (assetId ? getAsset(assetId) : Promise.resolve(null)),
    enabled: !!assetId,
  });

  return {
    assetId: assetId ?? null,
    asset: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
  };
}
