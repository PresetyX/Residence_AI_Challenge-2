"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EventSidebar } from "@/components/sidebar/event-sidebar";
import { Toaster } from "@/components/ui/toaster";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import { ChatHeader } from "./chat-header";
import { Composer } from "./composer";
import { MessageList } from "./message-list";

export function ChatScreen() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const hydrated = useAuthStore((state) => state.hydrated);
  const isSidebarOpen = useUiStore((state) => state.panelView !== "closed");

  // Route guard: /chat is only reachable with a session.
  useEffect(() => {
    if (hydrated && !user) router.replace("/");
  }, [hydrated, user, router]);

  if (!hydrated || !user) {
    return (
      <div className="grid h-dvh place-items-center" role="status">
        <LoaderCircle className="size-6 animate-spin text-violet-400" aria-hidden="true" />
        <span className="sr-only">Carregando…</span>
      </div>
    );
  }

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-64 left-1/2 size-[40rem] -translate-x-1/2 rounded-full bg-violet-700/15 blur-[140px]" />
      </div>

      <ChatHeader user={user} />

      {/* On large screens the thread makes room for the docked drawer. */}
      <main
        className={`relative flex min-h-0 flex-1 flex-col transition-[padding] duration-300 ease-out ${
          isSidebarOpen ? "lg:pr-[26rem]" : ""
        }`}
      >
        <MessageList userFirstName={user.name.split(" ")[0]} />
        <Composer />
      </main>

      <EventSidebar />
      <Toaster />
    </div>
  );
}
