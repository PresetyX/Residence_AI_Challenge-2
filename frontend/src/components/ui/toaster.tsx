"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CircleAlert, CircleCheck, Info, type LucideIcon, X } from "lucide-react";
import { type ToastTone, useToastStore } from "@/store/toast-store";

const TONE: Record<ToastTone, { icon: LucideIcon; className: string }> = {
  success: { icon: CircleCheck, className: "text-emerald-300" },
  error: { icon: CircleAlert, className: "text-red-300" },
  info: { icon: Info, className: "text-violet-300" },
};

export function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div
      role="region"
      aria-label="Notificações"
      className="pointer-events-none fixed inset-x-0 bottom-24 z-[70] flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-5 sm:bottom-5 sm:items-end"
    >
      <AnimatePresence>
        {toasts.map((toast) => {
          const tone = TONE[toast.tone];
          const Icon = tone.icon;
          return (
            <motion.div
              key={toast.id}
              layout
              role={toast.tone === "error" ? "alert" : "status"}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
              className="glass glow pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl py-3 pr-2 pl-4"
            >
              <Icon className={`mt-0.5 size-4.5 shrink-0 ${tone.className}`} aria-hidden="true" />
              <p className="min-w-0 flex-1 text-sm leading-snug text-slate-100">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                aria-label="Dispensar notificação"
                className="grid size-7 shrink-0 place-items-center rounded-full text-muted transition hover:bg-white/10 hover:text-white"
              >
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
