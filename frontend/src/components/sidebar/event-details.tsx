"use client";

import {
  AlignLeft,
  CircleAlert,
  CircleCheck,
  Clock,
  ExternalLink,
  Hand,
  LoaderCircle,
  type LucideIcon,
  MapPin,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";
import { formatDuration, formatLongDate, formatShortDate, formatTime } from "@/lib/format";
import type { CalendarEvent, SyncStatus } from "@/lib/types";

const SYNC_META: Record<
  SyncStatus,
  { icon: LucideIcon; label: string; hint: string; className: string; spin?: boolean }
> = {
  synced: {
    icon: CircleCheck,
    label: "Sincronizado",
    hint: "O evento está atualizado no Google Agenda.",
    className: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  },
  pending: {
    icon: LoaderCircle,
    label: "Sincronizando…",
    hint: "Enviando as alterações para o Google Agenda.",
    className: "border-amber-400/30 bg-amber-500/10 text-amber-200",
    spin: true,
  },
  error: {
    icon: CircleAlert,
    label: "Falha na sincronização",
    hint: "As últimas alterações não chegaram ao Google Agenda. Tente editar novamente.",
    className: "border-red-400/30 bg-red-500/10 text-red-200",
  },
};

export function EventDetails({ event }: { event: CalendarEvent }) {
  const sync = SYNC_META[event.syncStatus];
  const SyncIcon = sync.icon;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium tracking-wider text-violet-400 uppercase">
          Título do evento
        </p>
        <h3 className="mt-1.5 font-display text-2xl leading-tight font-semibold break-words">
          {event.title}
        </h3>
        <p className="mt-1.5 text-sm text-muted first-letter:uppercase">
          {formatLongDate(event.start)}
        </p>
        <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-violet-600/10 px-2.5 py-1 text-xs text-violet-200">
          {event.planGoal ? (
            <>
              <Sparkles className="size-3.5" aria-hidden="true" />
              Bloco do plano “{event.planGoal}”
            </>
          ) : (
            <>
              <Hand className="size-3.5" aria-hidden="true" />
              Criado manualmente
            </>
          )}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <TimeBox label="Início" iso={event.start} />
        <TimeBox label="Término" iso={event.end} />
        <p className="col-span-2 flex items-center gap-2 text-xs text-muted">
          <Clock className="size-3.5 text-violet-400" aria-hidden="true" />
          Duração: {formatDuration(event.start, event.end)}
        </p>
      </div>

      <dl className="space-y-5">
        <Field icon={AlignLeft} label="Descrição">
          {event.description ? (
            <span className="break-words whitespace-pre-wrap">{event.description}</span>
          ) : (
            <Empty>Sem descrição</Empty>
          )}
        </Field>
        <Field icon={MapPin} label="Localização">
          {event.location || <Empty>Sem localização definida</Empty>}
        </Field>
        <Field icon={RefreshCw} label="Status de sincronização da agenda">
          <span
            role="status"
            className={`mt-1 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${sync.className}`}
          >
            <SyncIcon className={`size-3.5 ${sync.spin ? "animate-spin" : ""}`} aria-hidden="true" />
            {sync.label}
          </span>
          <span className="mt-2 block text-xs text-muted">
            {sync.hint} Última atualização: {formatShortDate(event.updatedAt)} às{" "}
            {formatTime(event.updatedAt)}.
          </span>
        </Field>
      </dl>

      {event.link && (
        <a
          href={event.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-purple-500/25 bg-white/5 text-sm font-medium transition hover:border-purple-400/50 hover:bg-white/10"
        >
          Abrir no Google Agenda
          <ExternalLink className="size-4" aria-hidden="true" />
          <span className="sr-only">(abre em nova aba)</span>
        </a>
      )}
    </div>
  );
}

function TimeBox({ label, iso }: { label: string; iso: string }) {
  return (
    <div className="rounded-2xl border border-purple-500/20 bg-ink-950/60 p-3.5">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 font-display text-xl font-semibold tabular-nums">
        <time dateTime={iso}>{formatTime(iso)}</time>
      </p>
      <p className="text-xs text-muted">{formatShortDate(iso)}</p>
    </div>
  );
}

function Field({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-violet-600/15 text-violet-300">
        <Icon className="size-4" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <dt className="text-xs text-muted">{label}</dt>
        <dd className="mt-0.5 text-sm leading-relaxed text-slate-100">{children}</dd>
      </div>
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <span className="text-slate-500">{children}</span>;
}
