import { create } from "zustand";
import { persist } from "zustand/middleware";
import { SYSTEM_PROMPT } from "@/lib/assistant-rules";
import { createId } from "@/lib/format";
import { DEFAULT_MODEL_ID } from "@/lib/models";
import type { ChatMessage, ModelId } from "@/lib/types";
import { ApiError, isAbortError, request } from "@/services/http";
import { resetProjectPlanner } from "@/services/project-planner";
import { inferenceService } from "@/services/inference-service";
import { pendingOnboarding, startOnboarding } from "@/services/onboarding";
import { useCalendarStore } from "./calendar-store";

interface ChatState {
  messages: ChatMessage[];
  selectedModelId: ModelId;
  isGenerating: boolean;
  /** The last reply settled the request: the next message starts a fresh conversation. */
  conversationEnded: boolean;
  selectModel: (modelId: ModelId) => void;
  sendMessage: (text: string) => Promise<void>;
  stopGenerating: () => void;
  resetConversation: () => void;
  /** Opens the chat with the first-run questions (sleep, calibration) when the profile lacks them. */
  beginOnboarding: (account: { email: string; name: string }) => Promise<void>;
}

// Kept outside the store: an AbortController is not serializable state.
let activeRequest: AbortController | null = null;

/** Clears every pending step: the planner flow here and the Supervisor's "sim/não" on the backend. */
function startOver(): Promise<void> {
  resetProjectPlanner();
  return request<void>("/chat/reiniciar", { method: "POST" }).catch(() => undefined);
}

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
        conversationEnded: false,

        selectModel: (selectedModelId) => set({ selectedModelId }),

        async sendMessage(text) {
          const content = text.trim();
          if (!content || get().isGenerating) return;

          // The Supervisor has no memory: once a request is settled, a new message is a new chat.
          // Waits for the backend reset so it cannot wipe what this new message asks for.
          if (get().conversationEnded) {
            set({ messages: [], conversationEnded: false });
            await startOver();
          }

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
              } else if (chunk.type === "status") {
                patchMessage(reply.id, () => ({ statusText: chunk.value }));
              } else if (chunk.type === "project_plan") {
                patchMessage(reply.id, () => ({ projectPlan: chunk.plan }));
              } else if (chunk.type === "conversation_end") {
                patchMessage(reply.id, () => ({ endsConversation: true }));
                set({ conversationEnded: true });
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
                  (error instanceof ApiError
                    ? error.message
                    : "Não consegui gerar uma resposta agora. Verifique sua conexão e tente novamente."),
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

        async beginOnboarding(account) {
          const greeting = await startOnboarding(account);
          if (!greeting || get().messages.length > 0) return;
          const message: ChatMessage = {
            id: createId("msg"),
            role: "assistant",
            content: greeting,
            createdAt: new Date().toISOString(),
            status: "done",
          };
          set({ messages: [message] });
        },

        resetConversation() {
          activeRequest?.abort();
          void startOver();
          set({ messages: [], isGenerating: false, conversationEnded: false });
          // Questions still unanswered: ask them again in the new, empty thread.
          const account = pendingOnboarding();
          if (account) void get().beginOnboarding(account).catch(() => undefined);
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
