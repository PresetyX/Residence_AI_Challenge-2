"use client";

import { motion } from "framer-motion";
import { CalendarPlus, Eye, GraduationCap, type LucideIcon, Target } from "lucide-react";
import { LogoMark } from "@/components/ui/logo";
import { useChatStore } from "@/store/chat-store";
import { useUiStore } from "@/store/ui-store";

interface Suggestion {
  icon: LucideIcon;
  title: string;
  /** Text shown on the card; sent as a chat message unless `manual` is set. */
  prompt: string;
  /** Opens the manual creation form instead of sending a message. */
  manual?: boolean;
}

const SUGGESTIONS: Suggestion[] = [
  {
    icon: Target,
    title: "Planejar um projeto até o prazo",
    prompt:
      "Quero criar um projeto de inteligência artificial para análise de sentimentos em redes sociais, com prazo até 31/12/2026",
  },
  {
    icon: GraduationCap,
    title: "Blocos de foco na semana",
    prompt: "Monte um plano para eu fazer meu TCC, tenho 10 horas livres esta semana",
  },
  {
    icon: Eye,
    title: "Ver horários livres",
    prompt: "Quais horários livres eu tenho amanhã?",
  },
  {
    icon: CalendarPlus,
    title: "Compromisso simples",
    prompt: "Crie manualmente no painel Agenda",
    manual: true,
  },
];

export function EmptyState({ userFirstName }: { userFirstName: string }) {
  const sendMessage = useChatStore((state) => state.sendMessage);
  const openCreateForm = useUiStore((state) => state.openCreateForm);

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col items-center justify-center py-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative"
      >
        <span
          aria-hidden="true"
          className="animate-pulse-glow absolute -inset-10 rounded-full bg-violet-600/40 blur-3xl"
        />
        <LogoMark className="relative h-20" />
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="mt-7 font-display text-2xl font-semibold tracking-tight text-balance sm:text-3xl"
      >
        Olá, {userFirstName}. O que vamos <span className="text-gradient">destravar</span> hoje?
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18, duration: 0.5 }}
        className="mt-3 text-muted"
      >
        Descreva o projeto e o prazo: eu divido em etapas com story points. Ou diga quantas horas livres tem e eu monto blocos de foco na agenda.
      </motion.p>

      <ul className="mt-9 grid w-full gap-3 text-left sm:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, title, prompt, manual }, index) => (
          <motion.li
            key={title}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + index * 0.07, duration: 0.45 }}
          >
            <button
              type="button"
              onClick={() => (manual ? openCreateForm() : void sendMessage(prompt))}
              aria-haspopup={manual ? "dialog" : undefined}
              className="group flex h-full w-full items-start gap-3 rounded-2xl border border-purple-500/20 bg-ink-900/70 p-4 text-left transition hover:-translate-y-0.5 hover:border-violet-400/60 hover:bg-violet-600/10 hover:shadow-[0_10px_40px_-16px_rgb(124_58_237/0.9)]"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-violet-600/20 text-violet-300 transition group-hover:bg-violet-600 group-hover:text-white">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-sm font-medium text-white">{title}</span>
                <span className="mt-0.5 block text-sm text-muted">
                  {manual ? prompt : `“${prompt}”`}
                </span>
              </span>
            </button>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
