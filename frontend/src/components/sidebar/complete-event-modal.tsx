"use client";

import { Check, CircleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatLongDate, formatTimeRange } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { toast } from "@/store/toast-store";

interface CompleteEventModalProps {
  event: CalendarEvent;
  open: boolean;
  onClose: () => void;
}

/** Second check before a plan step is marked as done. Nothing is deleted. */
export function CompleteEventModal({ event, open, onClose }: CompleteEventModalProps) {
  const completeEvent = useCalendarStore((state) => state.completeEvent);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) setError(null);
  }, [open]);

  async function handleConfirm() {
    setSaving(true);
    setError(null);
    try {
      await completeEvent(event.id);
      onClose();
      toast.success(`Tarefa “${event.title}” marcada como concluída.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível concluir a tarefa.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      busy={saving}
      title="Você concluiu mesmo esta tarefa?"
      description="Ela ficará marcada como feita. O agendamento continua na sua agenda."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving} data-autofocus>
            Ainda não
          </Button>
          <Button
            onClick={handleConfirm}
            loading={saving}
            icon={<Check className="size-4" aria-hidden="true" />}
          >
            {saving ? "Salvando…" : "Sim, concluí"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4">
          <p className="font-display font-semibold break-words">{event.title}</p>
          <p className="mt-1.5 text-sm text-slate-300 first-letter:uppercase">
            {formatLongDate(event.start)} · {formatTimeRange(event.start, event.end)}
          </p>
        </div>
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
