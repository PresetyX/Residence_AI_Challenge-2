"use client";

import { CalendarDays, CircleAlert, Clock, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatLongDate, formatTimeRange } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { buildDeletePayload } from "@/services/calendar-service";
import { useCalendarStore } from "@/store/calendar-store";
import { toast } from "@/store/toast-store";
import { useUiStore } from "@/store/ui-store";

interface DeleteEventModalProps {
  event: CalendarEvent;
  open: boolean;
  onClose: () => void;
}

export function DeleteEventModal({ event, open, onClose }: DeleteEventModalProps) {
  const deleteEvent = useCalendarStore((state) => state.deleteEvent);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Built once per opening: what the user reviews here is exactly what gets sent.
  // eslint-disable-next-line react-hooks/exhaustive-deps -- rebuild only when the modal opens
  const payload = useMemo(() => buildDeletePayload(event), [open, event.id]);

  useEffect(() => {
    if (open) setError(null);
  }, [open]);

  async function handleConfirm() {
    setDeleting(true);
    setError(null);
    try {
      await deleteEvent(payload);
      useUiStore.getState().goBack();
      toast.success(`Agendamento “${event.title}” excluído da sua agenda.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível excluir o agendamento.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      busy={deleting}
      title="Excluir agendamento?"
      description="O evento será removido do seu Google Agenda. Esta ação não pode ser desfeita."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={deleting} data-autofocus>
            Cancelar
          </Button>
          <Button variant="danger" onClick={handleConfirm} loading={deleting}>
            {deleting ? "Excluindo…" : "Excluir agendamento"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex gap-3 rounded-2xl border border-red-500/25 bg-red-500/10 p-4">
          <TriangleAlert className="mt-0.5 size-5 shrink-0 text-red-300" aria-hidden="true" />
          <div className="min-w-0">
            <p className="font-display font-semibold break-words">{event.title}</p>
            <p className="mt-1.5 flex items-center gap-2 text-sm text-slate-300">
              <CalendarDays className="size-3.5 shrink-0" aria-hidden="true" />
              <span className="first-letter:uppercase">{formatLongDate(event.start)}</span>
            </p>
            <p className="mt-1 flex items-center gap-2 text-sm text-slate-300">
              <Clock className="size-3.5 shrink-0" aria-hidden="true" />
              {formatTimeRange(event.start, event.end)}
            </p>
          </div>
        </div>

        <details className="group rounded-2xl border border-purple-500/20 bg-ink-950/60">
          <summary className="list-none rounded-2xl px-4 py-3 text-sm text-muted transition hover:text-white [&::-webkit-details-marker]:hidden">
            <span className="mr-1.5 inline-block transition-transform group-open:rotate-90">›</span>
            Ver dados enviados à API
          </summary>
          <div className="border-t border-purple-500/15 px-4 py-3">
            <p className="font-mono text-xs break-all text-violet-200">
              DELETE /calendar/events/{payload.evento_id}
            </p>
            <pre
              tabIndex={0}
              aria-label="Payload da requisição de exclusão"
              className="mt-2 overflow-x-auto font-mono text-xs leading-relaxed text-slate-300"
            >
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>
        </details>

        {error && (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-200"
          >
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
