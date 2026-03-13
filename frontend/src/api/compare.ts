import { postGenerateImage } from "./generation.js";
import { postGenerateMesh } from "./mesh.js";

export interface CompareImageRequest {
  prompt: string;
  negative_prompt?: string;
  width: number;
  height: number;
  provider_key_a: string;
  provider_key_b: string;
}

export interface CompareMeshRequest {
  source_image_url: string;
  provider_key_a: string;
  provider_key_b: string;
  params_a?: Record<string, unknown>;
  params_b?: Record<string, unknown>;
}

/**
 * Startet zwei parallele Bildgenerierungs-Jobs.
 * @returns [job_id_a, job_id_b]
 */
export async function startImageCompare(
  req: CompareImageRequest
): Promise<[string, string]> {
  const [resA, resB] = await Promise.all([
    postGenerateImage({
      prompt: req.prompt,
      model_key: req.provider_key_a,
      width: req.width,
      height: req.height,
      negative_prompt: req.negative_prompt,
    }),
    postGenerateImage({
      prompt: req.prompt,
      model_key: req.provider_key_b,
      width: req.width,
      height: req.height,
      negative_prompt: req.negative_prompt,
    }),
  ]);
  return [resA.job_id, resB.job_id];
}

/**
 * Startet zwei parallele Mesh-Generierungs-Jobs.
 * @returns [job_id_a, job_id_b]
 */
export async function startMeshCompare(
  req: CompareMeshRequest
): Promise<[string, string]> {
  const [resA, resB] = await Promise.all([
    postGenerateMesh({
      source_image_url: req.source_image_url,
      provider_key: req.provider_key_a,
      params: req.params_a ?? {},
    }),
    postGenerateMesh({
      source_image_url: req.source_image_url,
      provider_key: req.provider_key_b,
      params: req.params_b ?? {},
    }),
  ]);
  return [resA.job_id, resB.job_id];
}
