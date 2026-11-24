"use client";

import { CalendarDays, CircleAlert, FileText, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/ui/google-icon";
import { Modal } from "@/components/ui/modal";
import { CALENDAR_CONSENT_POINTS, TERMS_SECTIONS, TERMS_VERSION } from "@/lib/legal";
import { useAuthStore } from "@/store/auth-store";

interface ConsentModalProps {
  open: boolean;
  onClose: () => void;
}

export function ConsentModal({ open, onClose }: ConsentModalProps) {
  const router = useRouter();
  const signIn = useAuthStore((state) => state.signIn);
  const status = useAuthStore((state) => state.status);
  const error = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);

  const [termsAccepted, setTermsAccepted] = useState(false);
  const [calendarAccepted, setCalendarAccepted] = useState(false);

  const isLoading = status === "loading";
  const canContinue = termsAccepted && calendarAccepted;

  // Consent is asked fresh every time the modal opens.
  useEffect(() => {
    if (open) {
      setTermsAccepted(false);
      setCalendarAccepted(false);
      clearError();
    }
  }, [open, clearError]);

  async function handleContinue() {
    if (!canContinue) return;
    const signedIn = await signIn({
      termsAccepted,
      calendarAccessAccepted: calendarAccepted,
      termsVersion: TERMS_VERSION,
      acceptedAt: new Date().toISOString(),
    });
    if (signedIn) router.push("/chat");
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      busy={isLoading}
      size="lg"
      title="Antes de entrar"
      description="Para usar o Destrava, precisamos da sua autorização para acessar o Google Agenda e do seu aceite dos termos."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            onClick={handleContinue}
            disabled={!canContinue}
            loading={isLoading}
            aria-describedby="consent-hint"
            icon={
              <span className="grid size-6 place-items-center rounded-full bg-white">
                <GoogleIcon className="size-3.5" />
              </span>
            }
          >
            {isLoading ? "Conectando ao Google…" : "Continuar com o Google"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <section aria-labelledby="consent-calendar-title">
          <SectionTitle id="consent-calendar-title" icon={<CalendarDays className="size-4" />}>
            Acesso ao Google Agenda
          </SectionTitle>
          <div className="mt-3 rounded-2xl border border-purple-500/25 bg-violet-600/10 p-4">
            <p className="text-sm leading-relaxed text-slate-200">
              Ao continuar, o aplicativo solicitará permissão de{" "}
              <strong className="font-semibold text-white">leitura e escrita</strong> no seu Google
              Agenda por meio da API do Google Calendar.
            </p>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {CALENDAR_CONSENT_POINTS.map((point) => (
                <li key={point} className="flex gap-2.5">
                  <ShieldCheck
                    className="mt-0.5 size-4 shrink-0 text-violet-400"
                    aria-hidden="true"
                  />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="consent-terms-title">
          <SectionTitle id="consent-terms-title" icon={<FileText className="size-4" />}>
            Termos de Serviço e Política de Privacidade
          </SectionTitle>
          <div
            tabIndex={0}
            role="region"
            aria-labelledby="consent-terms-title"
            className="mt-3 max-h-56 space-y-4 overflow-y-auto rounded-2xl border border-purple-500/20 bg-ink-950/60 p-4 text-sm leading-relaxed text-muted"
          >
            {TERMS_SECTIONS.map((section) => (
              <div key={section.title}>
                <h4 className="font-medium text-white">{section.title}</h4>
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph} className="mt-1.5">
                    {paragraph}
                  </p>
                ))}
              </div>
            ))}
            <p className="text-xs text-slate-500">Versão dos termos: {TERMS_VERSION}</p>
          </div>
        </section>

        <fieldset className="space-y-3" disabled={isLoading}>
          <legend className="sr-only">Aceites obrigatórios</legend>
          <ConsentCheckbox checked={termsAccepted} onChange={setTermsAccepted}>
            Concordo com os Termos de Serviço
            <span className="block text-xs font-normal text-muted">
              Li e aceito os Termos de Serviço e a Política de Privacidade.
            </span>
          </ConsentCheckbox>
          <ConsentCheckbox checked={calendarAccepted} onChange={setCalendarAccepted}>
            Autorizo a integração com o Google Agenda
            <span className="block text-xs font-normal text-muted">
              Permito a leitura e a escrita de eventos na minha agenda via API.
            </span>
          </ConsentCheckbox>
        </fieldset>

        <p id="consent-hint" className="text-xs text-muted" aria-live="polite">
          {canContinue
            ? "Tudo certo. Você será direcionado ao login do Google."
            : "Marque as duas opções acima para liberar o login com o Google."}
        </p>

        {error && (
          <p
            role="alert"
            className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-200"
          >
            <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

function SectionTitle({ id, icon, children }: { id: string; icon: ReactNode; children: ReactNode }) {
  return (
    <h3 id={id} className="flex items-center gap-2 text-sm font-semibold text-white">
      <span className="grid size-7 place-items-center rounded-lg bg-violet-600/25 text-violet-300">
        {icon}
      </span>
      {children}
    </h3>
  );
}

function ConsentCheckbox({
  checked,
  onChange,
  autoFocus = false,
  children,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  autoFocus?: boolean;
  children: ReactNode;
}) {
  return (
    <label
      className={`flex cursor-pointer items-start gap-3 rounded-2xl border p-3.5 transition ${
        checked
          ? "border-violet-400/60 bg-violet-600/15"
          : "border-purple-500/20 bg-white/[0.03] hover:border-purple-400/40"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        data-autofocus={autoFocus || undefined}
        className="mt-0.5 size-4.5 shrink-0 cursor-pointer accent-violet-500"
      />
      <span className="text-sm font-medium text-white">{children}</span>
    </label>
  );
}
