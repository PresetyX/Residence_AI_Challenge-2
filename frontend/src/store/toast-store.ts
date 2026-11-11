import { create } from "zustand";
import { createId } from "@/lib/format";

export type ToastTone = "success" | "error" | "info";

export interface Toast {
  id: string;
  tone: ToastTone;
  message: string;
}

interface ToastState {
  toasts: Toast[];
  show: (message: string, tone?: ToastTone) => void;
  dismiss: (id: string) => void;
}

const VISIBLE_MS = 4500;

export const useToastStore = create<ToastState>()((set, get) => ({
  toasts: [],
  show(message, tone = "success") {
    const id = createId("toast");
    // Keep at most three on screen; the oldest gives way.
    set((state) => ({ toasts: [...state.toasts.slice(-2), { id, tone, message }] }));
    setTimeout(() => get().dismiss(id), VISIBLE_MS);
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}));

/** Shorthand for use outside React components. */
export const toast = {
  success: (message: string) => useToastStore.getState().show(message, "success"),
  error: (message: string) => useToastStore.getState().show(message, "error"),
  info: (message: string) => useToastStore.getState().show(message, "info"),
};
