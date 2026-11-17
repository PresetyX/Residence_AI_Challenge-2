import type { ModelId, ModelOption } from "./types";

export const MODELS: ModelOption[] = [
  {
    id: "gemma-2b",
    name: "Gemma 4 E2B (Q4_K_M / 4-bit)",
    shortName: "Gemma 4 E2B",
    description: "Leve e rápido",
    runtime: "cloud",
  },
  {
    id: "gemma-4-26b-a4b-q4_0",
    name: "Gemma 4 26B A4B (Q4_K_M / 4-bit)",
    shortName: "Gemma 4 26B A4B",
    description: "Alta performance",
    runtime: "cloud",
  },
  {
    id: "gemma-4-12b-sfp8",
    name: "Gemma 4 12B (Q4_K_M / 4-bit)",
    shortName: "Gemma 4 12B",
    description: "Precisão balanceada",
    runtime: "cloud",
  },
];

export const DEFAULT_MODEL_ID: ModelId = "gemma-2b";

export function getModel(id: ModelId): ModelOption {
  return MODELS.find((model) => model.id === id) ?? MODELS[0];
}
