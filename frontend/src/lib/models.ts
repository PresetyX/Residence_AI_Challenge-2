import type { ModelId, ModelOption } from "./types";

export const MODELS: ModelOption[] = [
  {
    id: "gemma-2b",
    name: "Gemma 2B",
    shortName: "Gemma 2B",
    description: "Execução local no dispositivo",
    runtime: "local",
  },
  {
    id: "gemma-4-26b-a4b-q4_0",
    name: "Gemma 4 26B A4B (Quantização Q4_0 / 4-bit)",
    shortName: "Gemma 4 26B A4B",
    description: "Execução na nuvem (Alta performance)",
    runtime: "cloud",
  },
  {
    id: "gemma-4-12b-sfp8",
    name: "Gemma 4 12B (Quantização SFP8 / 8-bit)",
    shortName: "Gemma 4 12B",
    description: "Execução na nuvem (Precisão balanceada)",
    runtime: "cloud",
  },
];

export const DEFAULT_MODEL_ID: ModelId = "gemma-2b";

export function getModel(id: ModelId): ModelOption {
  return MODELS.find((model) => model.id === id) ?? MODELS[0];
}
