"use client";

import { motion } from "framer-motion";
import { CalendarRange, ChevronRight } from "lucide-react";
import { formatShortDate, formatTimeRange } from "@/lib/format";
import type { CalendarAction, CalendarActionType } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { useUiStore } from "@/store/ui-store";

const ACTION_LABEL: Record<CalendarActionType, { label: string; className: string }> = {
  created: { label: "Criado", className: "bg-emerald-500/10 text-emerald-300" },
  updated: { label: "Ajustado", className: "bg-sky-500/10 text-sky-300" },
  deleted: { label: "Removido", className: "bg-red-500/10 text-red-300" },
};

function summarize(actions: CalendarAction[]): string {
  const count = (type: CalendarActionType) => actions.filter((action) => action.type === type).length;
  const part = (total: number, one: string, many: string) =>
    total > 0 ? `${total} ${total === 1 ? one : many}` : null;
  return [
    part(count("created"), "bloco criado", "blocos criados"),
    part(count("updated"), "bloco ajustado", "blocos ajustados"),
    part(count("deleted"), "bloco removido", "blocos removidos"),
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Inline card for a batch of calendar changes made by an AI plan. */
export function CalendarPlanCard({ actions }: { actions: CalendarAction[] }) {
  const goal = actions[0]?.snapshot.planGoal;

  return (
    <motion.article
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      aria-label={goal ? `Plano ${goal}` : "Alterações na agenda"}
      className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-purple-500/25 bg-ink-900/80 shadow-[0_10px_40px_-20px_rgb(124_58_237/0.7)] backdrop-blur"
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-400 to-violet-700"
      />
      <header className="flex items-center gap-3 border-b border-purple-500/15 py-3.5 pr-4 pl-5">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-violet-600/20 text-violet-300">
          <CalendarRange className="size-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="truncate font-display font-semibold">
            {goal ? `Plano: ${goal}` : "Alterações na agenda"}
          </p>
          <p className="text-xs text-muted">{summarize(actions)}</p>
        </div>
      </header>
      <ul className="divide-y divide-purple-500/10">
        {actions.map((action) => (
          <PlanRow key={`${action.type}-${action.eventId}`} action={action} />
        ))}
      </ul>
    </motion.article>
  );
}

function PlanRow({ action }: { action: CalendarAction }) {
  // Prefer the live event so later edits (manual or by a replan) show up here too.
  const liveEvent = useCalendarStore((state) => state.events[action.eventId]);
  const isDeleted = useCalendarStore((state) => Boolean(state.deletedIds[action.eventId]));
  const isActive = useUiStore((state) => state.activeEventId === action.eventId);
  const openEventDetails = useUiStore((state) => state.openEventDetails);

  const removedHere = action.type === "deleted";
  const removed = removedHere || isDeleted;
  const event = removedHere || !liveEvent ? action.snapshot : liveEvent;
  const badge = removed && !removedHere ? ACTION_LABEL.deleted : ACTION_LABEL[action.type];
  const phase = event.title.split(": ")[1] ?? event.title;

  return (
    <li
      className={`flex items-center gap-3 py-2.5 pr-3 pl-5 transition-colors ${isActive ? "bg-violet-600/15" : ""}`}
    >
      <div className={`min-w-0 flex-1 ${removed ? "opacity-55" : ""}`}>
        <p className={`truncate text-sm font-medium text-white ${removed ? "line-through" : ""}`}>
          <span className="sr-only">Título: </span>
          {phase}
        </p>
        <p className="mt-0.5 text-xs text-muted tabular-nums">
          <span className="sr-only">Data: </span>
          {formatShortDate(event.start)}
          <span aria-hidden="true"> · </span>
          <span className="sr-only">Horário: </span>
          {formatTimeRange(event.start, event.end)}
        </p>
      </div>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[0.68rem] font-medium ${badge.className}`}>
        {removed && !removedHere ? "Removido depois" : badge.label}
      </span>
      {removed ? (
        <span className="w-[8.2rem] shrink-0" aria-hidden="true" />
      ) : (
        <button
          type="button"
          onClick={() => openEventDetails(action.eventId)}
          aria-haspopup="dialog"
          aria-label={`Mais informações sobre ${event.title}`}
          className="group inline-flex h-8 w-[8.2rem] shrink-0 items-center justify-center gap-1 rounded-lg border border-purple-500/30 bg-violet-600/10 text-xs font-medium text-violet-100 transition hover:border-violet-400/70 hover:bg-violet-600/25 hover:text-white"
        >
          Mais informações
          <ChevronRight
            className="size-3.5 transition-transform group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </button>
      )}
    </li>
  );
}
