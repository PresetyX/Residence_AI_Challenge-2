import { create } from "zustand";
import { persist } from "zustand/middleware";
import { SYSTEM_PROMPT } from "@/lib/assistant-rules";
import { createId } from "@/lib/format";
import { DEFAULT_MODEL_ID } from "@/lib/models";
import type { ChatMessage, ModelId } from "@/lib/types";
import { isAbortError } from "@/services/http";
import { inferenceService } from "@/services/inference-service";
import { useCalendarStore } from "./calendar-store";

interface ChatState {
  messages: ChatMessage[];
  selectedModelId: ModelId;
  isGenerating: boolean;
  selectModel: (modelId: ModelId) => void;
  sendMessage: (text: string) => Promise<void>;
  stopGenerating: () => void;
  resetConversation: () => void;
}

// Kept outside the store: an AbortController is not serializable state.
let activeRequest: AbortController | null = null;

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
      const patchMessage = (id: string, patch: (message: ChatMessage) => Partial<ChatMessage>) =>
        set((state) => ({
          messages: state.messages.map((message) =>
            message.id === id ? { ...message, ...patch(message) } : message,
          ),
        }));

      return {
        messages: [],
        selectedModelId: DEFAULT_MODEL_ID,
        isGenerating: false,

        selectModel: (selectedModelId) => set({ selectedModelId }),

        async sendMessage(text) {
          const content = text.trim();
          if (!content || get().isGenerating) return;

          const modelId = get().selectedModelId;
          const now = new Date().toISOString();
          const userMessage: ChatMessage = {
            id: createId("msg"),
            role: "user",
            content,
            createdAt: now,
            status: "done",
          };
          const reply: ChatMessage = {
            id: createId("msg"),
            role: "assistant",
            content: "",
            createdAt: now,
            status: "streaming",
            modelId,
          };

          const history = [...get().messages, userMessage].map(({ role, content: body }) => ({
            role,
            content: body,
          }));
          set((state) => ({
            messages: [...state.messages, userMessage, reply],
            isGenerating: true,
          }));

          const controller = new AbortController();
          activeRequest = controller;

          try {
            const stream = inferenceService.streamChat(
              { modelId, systemPrompt: SYSTEM_PROMPT, messages: history },
              controller.signal,
            );
            for await (const chunk of stream) {
              if (chunk.type === "token") {
                patchMessage(reply.id, (message) => ({ content: message.content + chunk.value }));
              } else if (chunk.type === "calendar_action") {
                useCalendarStore.getState().applyAction(chunk.action);
                patchMessage(reply.id, (message) => ({
                  calendarActions: [...(message.calendarActions ?? []), chunk.action],
                }));
              } else {
                patchMessage(reply.id, () => ({ suggestsManualPanel: true }));
              }
            }
            patchMessage(reply.id, () => ({ status: "done" }));
          } catch (error) {
            if (isAbortError(error)) {
              patchMessage(reply.id, (message) => ({
                status: "done",
                content: message.content || "*Resposta interrompida.*",
              }));
            } else {
              patchMessage(reply.id, (message) => ({
                status: "error",
                content:
                  message.content ||
                  "Não consegui gerar uma resposta agora. Verifique sua conexão e tente novamente.",
              }));
            }
          } finally {
            if (activeRequest === controller) activeRequest = null;
            set({ isGenerating: false });
          }
        },

        stopGenerating() {
          activeRequest?.abort();
        },

        resetConversation() {
          activeRequest?.abort();
          set({ messages: [], isGenerating: false });
        },
      };
    },
    {
      name: "destrava:chat",
      // Only the model preference survives reloads; the thread is session-scoped.
      partialize: ({ selectedModelId }) => ({ selectedModelId }),
      skipHydration: true,
    },
  ),
);
