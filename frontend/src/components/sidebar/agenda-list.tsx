"use client";

import { CalendarPlus, CalendarX2, ChevronRight, Hand, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { formatLongDate, formatTimeRange } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { useUiStore } from "@/store/ui-store";

/** Groups events by calendar day, in chronological order. */
function groupByDay(events: CalendarEvent[]): Array<{ day: string; events: CalendarEvent[] }> {
  const groups = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const day = formatLongDate(event.start);
    groups.set(day, [...(groups.get(day) ?? []), event]);
  }
  return [...groups].map(([day, dayEvents]) => ({ day, events: dayEvents }));
}

export function AgendaList() {
  const events = useCalendarStore((state) => state.events);
  const deletedIds = useCalendarStore((state) => state.deletedIds);
  const openCreateForm = useUiStore((state) => state.openCreateForm);
  const openEventDetails = useUiStore((state) => state.openEventDetails);

  const groups = useMemo(
    () =>
      groupByDay(
        Object.values(events)
          .filter((event) => !deletedIds[event.id])
          .sort((a, b) => a.start.localeCompare(b.start)),
      ),
    [events, deletedIds],
  );

  return (
    <div className="space-y-5">
      <Button
        onClick={openCreateForm}
        className="w-full"
        icon={<CalendarPlus className="size-4" aria-hidden="true" />}
      >
        Novo agendamento
      </Button>

      {groups.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-purple-500/25 px-5 py-10 text-center">
          <CalendarX2 className="mx-auto size-8 text-violet-400/70" aria-hidden="true" />
          <p className="mt-3 text-sm font-medium text-white">Nenhum agendamento por aqui</p>
          <p className="mt-1 text-sm text-muted">
            Crie um compromisso manualmente ou peça um plano no chat para preencher sua semana.
          </p>
        </div>
      ) : (
        groups.map((group) => (
          <section key={group.day} aria-label={group.day}>
            <h3 className="mb-2 text-xs font-medium tracking-wide text-muted first-letter:uppercase">
              {group.day}
            </h3>
            <ul className="space-y-2">
              {group.events.map((event) => (
                <li key={event.id}>
                  <button
                    type="button"
                    onClick={() => openEventDetails(event.id)}
                    className="group flex w-full items-center gap-3 rounded-2xl border border-purple-500/20 bg-ink-950/50 p-3 text-left transition hover:border-violet-400/60 hover:bg-violet-600/10"
                  >
                    <span
                      aria-hidden="true"
                      className={`h-10 w-1 shrink-0 rounded-full ${
                        event.planGoal
                          ? "bg-gradient-to-b from-violet-400 to-violet-700"
                          : "bg-slate-500"
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-white">
                        {event.title}
                      </span>
                      <span className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                        <span className="tabular-nums">
                          {formatTimeRange(event.start, event.end)}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          {event.planGoal ? (
                            <>
                              <Sparkles className="size-3 text-violet-400" aria-hidden="true" />
                              Plano
                            </>
                          ) : (
                            <>
                              <Hand className="size-3" aria-hidden="true" />
                              Manual
                            </>
                          )}
                        </span>
                      </span>
                    </span>
                    <ChevronRight
                      className="size-4 shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-white"
                      aria-hidden="true"
                    />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
