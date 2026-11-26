"use client";

import { Check, CircleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatLongDate, formatMinutes, formatTimeRange } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { toast } from "@/store/toast-store";

interface CompleteEventModalProps {
  event: CalendarEvent;
  open: boolean;
  onClose: () => void;
}

/** One calendar slot fits in a day; the backend refuses more than this. */
const MAX_MINUTES = 24 * 60;

/** Keeps only digits, so a negative or fractional time cannot be typed. */
const digits = (value: string) => value.replace(/\D/g, "").slice(0, 2);

/** Asks the time spent and checks again before a plan step is marked as done. */
export function CompleteEventModal({ event, open, onClose }: CompleteEventModalProps) {
  const completeEvent = useCalendarStore((state) => state.completeEvent);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState("");
  const [minutes, setMinutes] = useState("");

  const total = Number(hours || 0) * 60 + Number(minutes || 0);
  const invalid =
    Number(minutes || 0) > 59
      ? "Os minutos vão de 0 a 59."
      : total > MAX_MINUTES
        ? "O tempo não pode passar de 24 horas por agendamento."
        : null;
  const canConfirm = total > 0 && !invalid && !saving;

  useEffect(() => {
    if (!open) return;
    setError(null);
    setHours("");
    setMinutes("");
  }, [open, event.id]);

  async function handleConfirm() {
    if (!canConfirm) return;
    setSaving(true);
    setError(null);
    try {
      await completeEvent(event.id, total);
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
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Ainda não
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!canConfirm}
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
        <form
          onSubmit={(submit) => {
            submit.preventDefault();
            void handleConfirm();
          }}
        >
          <fieldset disabled={saving}>
            <legend className="text-sm font-medium">Quanto tempo você gastou?</legend>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <TimeField label="Horas" value={hours} onChange={setHours} autoFocus />
              <TimeField label="Minutos" value={minutes} onChange={setMinutes} />
            </div>
          </fieldset>
          <p aria-live="polite" className={`mt-2 text-xs ${invalid ? "text-red-300" : "text-muted"}`}>
            {invalid ??
              (total > 0 ? `Tempo informado: ${formatMinutes(total)}.` : "Informe o tempo para concluir.")}
          </p>
          {/* Lets Enter submit from either field. */}
          <button type="submit" hidden />
        </form>

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

function TimeField({
  label,
  value,
  onChange,
  autoFocus = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <label className="block text-xs text-muted">
      {label}
      <input
        type="text"
        inputMode="numeric"
        value={value}
        onChange={(change) => onChange(digits(change.target.value))}
        placeholder="0"
        data-autofocus={autoFocus || undefined}
        className="mt-1 h-11 w-full rounded-xl border border-purple-500/30 bg-ink-950/60 px-3 text-base text-white tabular-nums outline-none placeholder:text-slate-600 focus:border-emerald-300/70"
      />
    </label>
  );
}
