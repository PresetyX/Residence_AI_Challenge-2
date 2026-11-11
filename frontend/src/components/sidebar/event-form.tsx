"use client";

import { CircleAlert } from "lucide-react";
import { type FormEvent, type ReactNode, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { fromInputValues, toDateInputValue, toTimeInputValue } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { useCalendarStore } from "@/store/calendar-store";
import { toast } from "@/store/toast-store";

interface FormValues {
  title: string;
  description: string;
  location: string;
  date: string;
  startTime: string;
  endTime: string;
}

type FormErrors = Partial<Record<"title" | "date" | "startTime" | "endTime", string>>;

interface EventFormProps {
  /** Event being edited; omit to create a new one. */
  event?: CalendarEvent;
  onCancel: () => void;
  onSaved: (eventId: string) => void;
}

/** New events default to the next full hour, one hour long. */
function defaultValues(): FormValues {
  const start = new Date();
  start.setHours(start.getHours() + 1, 0, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    title: "",
    description: "",
    location: "",
    date: toDateInputValue(start.toISOString()),
    startTime: toTimeInputValue(start.toISOString()),
    // An event starting at 23:00 would end "before" it starts on the same day.
    endTime: end.getDate() === start.getDate() ? toTimeInputValue(end.toISOString()) : "23:59",
  };
}

function validate(values: FormValues, isNew: boolean): FormErrors {
  const errors: FormErrors = {};
  if (!values.title.trim()) errors.title = "Informe um título para o evento.";
  if (!values.date) errors.date = "Informe a data do evento.";
  if (!values.startTime || !values.endTime) {
    errors.endTime = "Informe os horários de início e de término.";
  } else if (values.endTime <= values.startTime) {
    errors.endTime = "O horário de término deve ser depois do início.";
  } else if (
    isNew &&
    values.date &&
    Date.parse(fromInputValues(values.date, values.startTime)) <= Date.now()
  ) {
    errors.startTime = "Não é possível criar eventos no passado.";
  }
  return errors;
}

export function EventForm({ event, onCancel, onSaved }: EventFormProps) {
  const createEvent = useCalendarStore((state) => state.createEvent);
  const updateEvent = useCalendarStore((state) => state.updateEvent);
  const formId = useId();
  const isNew = !event;

  const [values, setValues] = useState<FormValues>(() =>
    event
      ? {
          title: event.title,
          description: event.description,
          location: event.location,
          date: toDateInputValue(event.start),
          startTime: toTimeInputValue(event.start),
          endTime: toTimeInputValue(event.end),
        }
      : defaultValues(),
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (field: keyof FormValues) => (value: string) =>
    setValues((current) => ({ ...current, [field]: value }));

  async function onSubmit(submitEvent: FormEvent) {
    submitEvent.preventDefault();
    const nextErrors = validate(values, isNew);
    setErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) return;

    const input = {
      title: values.title.trim(),
      description: values.description.trim(),
      location: values.location.trim(),
      start: fromInputValues(values.date, values.startTime),
      end: fromInputValues(values.date, values.endTime),
    };

    setSaving(true);
    try {
      if (event) {
        await updateEvent(event.id, input);
        toast.success("Alterações salvas e sincronizadas com a agenda.");
        onSaved(event.id);
      } else {
        const id = await createEvent(input);
        toast.success(`Agendamento “${input.title}” criado na sua agenda.`);
        onSaved(id);
      }
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Não foi possível salvar o agendamento.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      {isNew && (
        <p className="rounded-xl border border-purple-500/20 bg-violet-600/10 px-3.5 py-3 text-sm leading-relaxed text-slate-300">
          Compromissos simples são criados aqui, por você. Para dividir uma meta em blocos de
          foco, peça um plano no chat.
        </p>
      )}

      <Field id={`${formId}-title`} label="Título" error={errors.title}>
        {(props) => (
          <input
            {...props}
            type="text"
            value={values.title}
            onChange={(e) => set("title")(e.target.value)}
            maxLength={120}
            required
            autoFocus
            placeholder={isNew ? "Ex.: Reunião de equipe" : undefined}
            className="field"
          />
        )}
      </Field>

      <Field id={`${formId}-description`} label="Descrição">
        {(props) => (
          <textarea
            {...props}
            value={values.description}
            onChange={(e) => set("description")(e.target.value)}
            rows={4}
            placeholder="Adicione detalhes, pauta ou links"
            className="field resize-y"
          />
        )}
      </Field>

      <Field id={`${formId}-date`} label="Data" error={errors.date}>
        {(props) => (
          <input
            {...props}
            type="date"
            value={values.date}
            onChange={(e) => set("date")(e.target.value)}
            required
            className="field"
          />
        )}
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field id={`${formId}-start`} label="Horário de início" error={errors.startTime}>
          {(props) => (
            <input
              {...props}
              type="time"
              value={values.startTime}
              onChange={(e) => set("startTime")(e.target.value)}
              required
              className="field"
            />
          )}
        </Field>
        <Field id={`${formId}-end`} label="Horário de término" error={errors.endTime}>
          {(props) => (
            <input
              {...props}
              type="time"
              value={values.endTime}
              onChange={(e) => set("endTime")(e.target.value)}
              required
              className="field"
            />
          )}
        </Field>
      </div>

      <Field id={`${formId}-location`} label="Localização">
        {(props) => (
          <input
            {...props}
            type="text"
            value={values.location}
            onChange={(e) => set("location")(e.target.value)}
            placeholder="Endereço ou link da chamada"
            className="field"
          />
        )}
      </Field>

      {submitError && (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-200"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {submitError}
        </p>
      )}

      <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
        <Button variant="ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
        <Button type="submit" loading={saving}>
          {saving ? "Salvando…" : isNew ? "Criar agendamento" : "Salvar alterações"}
        </Button>
      </div>
    </form>
  );
}

interface FieldControlProps {
  id: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: (props: FieldControlProps) => ReactNode;
}) {
  const errorId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-slate-300">
        {label}
      </label>
      {children({
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": error ? errorId : undefined,
      })}
      {error && (
        <p id={errorId} role="alert" className="mt-1.5 text-xs text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
