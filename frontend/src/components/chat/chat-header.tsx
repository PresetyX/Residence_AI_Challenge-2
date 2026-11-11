"use client";

import { CalendarDays, SquarePen } from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import type { User } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { useUiStore } from "@/store/ui-store";
import { useChatStore } from "@/store/chat-store";
import { ModelSelector } from "./model-selector";
import { UserMenu } from "./user-menu";

export function ChatHeader({ user }: { user: User }) {
  const hasMessages = useChatStore((state) => state.messages.length > 0);

  const eventCount = useCalendarStore(
    (state) => Object.keys(state.events).filter((id) => !state.deletedIds[id]).length,
  );
  const isAgendaOpen = useUiStore((state) => state.panelView !== "closed");
  const openAgenda = useUiStore((state) => state.openAgenda);
  const closePanel = useUiStore((state) => state.closePanel);

  // The calendar outlives the conversation: only the thread is cleared.
  const handleNewConversation = () => useChatStore.getState().resetConversation();

  return (
    <header className="relative z-30 flex h-16 shrink-0 items-center gap-3 border-b border-purple-500/15 bg-ink-950/80 px-3 backdrop-blur-xl sm:px-5">
      <Link href="/" aria-label="Destrava, página inicial" className="shrink-0">
        <Logo size="sm" hideTextOnMobile />
      </Link>
      <span aria-hidden="true" className="hidden h-6 w-px bg-purple-500/20 sm:block" />
      <ModelSelector />
      <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-3">
        <button
          type="button"
          onClick={isAgendaOpen ? closePanel : openAgenda}
          aria-haspopup="dialog"
          aria-expanded={isAgendaOpen}
          aria-label={`Agenda, ${eventCount} ${eventCount === 1 ? "agendamento" : "agendamentos"}`}
          title="Agenda: crie, edite e exclua agendamentos"
          className={`relative flex h-10 items-center gap-2 rounded-xl border px-3 text-sm transition ${
            isAgendaOpen
              ? "border-violet-400/70 bg-violet-600/20 text-white"
              : "border-purple-500/25 bg-white/5 text-slate-200 hover:border-purple-400/50 hover:bg-white/10 hover:text-white"
          }`}
        >
          <CalendarDays className="size-4 text-violet-300" aria-hidden="true" />
          <span className="hidden md:inline">Agenda</span>
          {eventCount > 0 && (
            <span
              aria-hidden="true"
              className="grid h-5 min-w-5 place-items-center rounded-full bg-violet-600 px-1.5 text-[0.68rem] font-semibold tabular-nums"
            >
              {eventCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={handleNewConversation}
          disabled={!hasMessages}
          aria-label="Nova conversa"
          title="Nova conversa"
          className="flex h-10 items-center gap-2 rounded-xl px-3 text-sm text-muted transition hover:bg-white/8 hover:text-white disabled:pointer-events-none disabled:opacity-40"
        >
          <SquarePen className="size-4" aria-hidden="true" />
          <span className="hidden md:inline">Nova conversa</span>
        </button>
        <UserMenu user={user} />
      </div>
    </header>
  );
}
