"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  CalendarCheck2,
  CalendarClock,
  CalendarDays,
  CalendarX2,
  Clock,
  type LucideIcon,
  Type,
} from "lucide-react";
import { formatDuration, formatLongDate, formatTimeRange } from "@/lib/format";
import type { CalendarAction, CalendarActionType } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { useUiStore } from "@/store/ui-store";

const ACTION_META: Record<CalendarActionType, { icon: LucideIcon; label: string; tone: string }> = {
  created: { icon: CalendarCheck2, label: "Evento criado", tone: "text-emerald-300 bg-emerald-500/10" },
  updated: { icon: CalendarClock, label: "Evento atualizado", tone: "text-sky-300 bg-sky-500/10" },
  deleted: { icon: CalendarX2, label: "Evento excluído", tone: "text-red-300 bg-red-500/10" },
};

export function CalendarEventCard({ action }: { action: CalendarAction }) {
  // Prefer the live event so manual edits in the drawer show up on existing cards.
  const liveEvent = useCalendarStore((state) => state.events[action.eventId]);
  const isDeleted = useCalendarStore((state) => Boolean(state.deletedIds[action.eventId]));
  const isActive = useUiStore((state) => state.activeEventId === action.eventId);
  const openEventDetails = useUiStore((state) => state.openEventDetails);

  const wasDeletedByThisAction = action.type === "deleted";
  const event = wasDeletedByThisAction || !liveEvent ? action.snapshot : liveEvent;
  const meta = ACTION_META[action.type];
  const Icon = meta.icon;
  const removed = wasDeletedByThisAction || isDeleted;

  return (
    <motion.article
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      aria-label={`${meta.label}: ${event.title}`}
      className={`relative w-full max-w-md overflow-hidden rounded-2xl border bg-ink-900/80 backdrop-blur transition-shadow ${
        isActive
          ? "border-violet-400/70 shadow-[0_0_40px_-10px_rgb(124_58_237/0.9)]"
          : "border-purple-500/25 shadow-[0_10px_40px_-20px_rgb(124_58_237/0.7)]"
      }`}
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-400 to-violet-700"
      />
      <div className="p-4 pl-5">
        <div className="flex flex-wrap items-center gap-2">
          <p
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${meta.tone}`}
          >
            <Icon className="size-3.5" aria-hidden="true" />
            {meta.label}
          </p>
          {removed && !wasDeletedByThisAction && (
            <p className="rounded-full bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-300">
              Excluído depois
            </p>
          )}
        </div>

        <dl className={`mt-3.5 space-y-2.5 text-sm ${removed ? "opacity-60" : ""}`}>
          <Row icon={Type} label="Título">
            <span className={`font-display font-semibold text-white ${removed ? "line-through" : ""}`}>
              {event.title}
            </span>
          </Row>
          <Row icon={CalendarDays} label="Data">
            <span className="first-letter:uppercase">{formatLongDate(event.start)}</span>
          </Row>
          <Row icon={Clock} label="Horário">
            {formatTimeRange(event.start, event.end)}
            <span className="text-muted"> · {formatDuration(event.start, event.end)}</span>
          </Row>
        </dl>

        {!removed && (
          <button
            type="button"
            onClick={() => openEventDetails(action.eventId)}
            aria-haspopup="dialog"
            className="group mt-4 inline-flex h-9 items-center gap-2 rounded-lg border border-purple-500/30 bg-violet-600/10 px-3.5 text-sm font-medium text-violet-100 transition hover:border-violet-400/70 hover:bg-violet-600/25 hover:text-white"
          >
            Mais informações
            <ArrowRight
              className="size-3.5 transition-transform group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </button>
        )}
      </div>
    </motion.article>
  );
}

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-violet-400" aria-hidden="true" />
      <dt className="w-16 shrink-0 text-muted">{label}</dt>
      <dd className="min-w-0 flex-1 text-slate-200">{children}</dd>
    </div>
  );
}
