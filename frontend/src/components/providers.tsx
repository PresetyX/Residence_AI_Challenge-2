"use client";

import { MotionConfig } from "framer-motion";
import { type ReactNode, useEffect } from "react";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore } from "@/store/chat-store";

export function Providers({ children }: { children: ReactNode }) {
  // Persisted stores are read after mount so the first client render matches the server.
  useEffect(() => {
    void useAuthStore.persist.rehydrate();
    void useChatStore.persist.rehydrate();
  }, []);

  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
