import type { ExecutionPlanItem } from "../api/presets.js";

type TabId =
  | "image"
  | "bgremoval"
  | "mesh"
  | "rigging"
  | "animation"
  | "mesh-processing";

/**
 * Mappt Preset-Step auf Pipeline-Tab oder Asset-Route.
 * Gibt { path, tab? } zurück.
 */
export function getRouteForStep(
  item: ExecutionPlanItem
): { path: string; tab?: TabId } {
  const step = item.step;
  const assetId = ""; // Wird vom Aufrufer ergänzt

  const pipelineSteps: Record<string, TabId> = {
    image: "image",
    bgremoval: "bgremoval",
    mesh: "mesh",
    clip_floor: "mesh-processing",
    remove_components: "mesh-processing",
    repair: "mesh-processing",
    simplify: "mesh-processing",
    rigging: "rigging",
    animation: "animation",
  };

  const tab = pipelineSteps[step];
  if (tab) {
    return { path: "/pipeline", tab };
  }

  // export, sketchfab_upload -> Asset-Modal (Bibliothek)
  if (step === "export" || step === "sketchfab_upload") {
    return { path: "/assets" };
  }

  return { path: "/pipeline", tab: "image" };
}

/**
 * Erstellt die Navigations-URL für den ersten ausstehenden Step.
 */
export function getUrlForFirstApplicableStep(
  executionPlan: ExecutionPlanItem[],
  assetId: string
): string {
  const first = executionPlan.find((i) => i.status === "applicable");
  if (!first) return `/assets?assetId=${assetId}`;

  const { path, tab } = getRouteForStep(first);
  if (path === "/assets") {
    return `/assets?assetId=${assetId}`;
  }
  return `/pipeline?tab=${tab ?? "image"}&assetId=${encodeURIComponent(assetId)}`;
}
