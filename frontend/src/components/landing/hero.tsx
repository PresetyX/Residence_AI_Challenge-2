"use client";

import { motion } from "framer-motion";
import {
  ArrowDown,
  ArrowRight,
  CalendarCheck2,
  CalendarDays,
  Clock,
  Cpu,
  RefreshCw,
  Sparkles,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/ui/google-icon";
import type { SignInProps } from "./landing-page";

const BADGES = [
  { icon: Target, label: "Metas em blocos de foco" },
  { icon: RefreshCw, label: "Replanejamento automático" },
  { icon: CalendarDays, label: "Google Agenda" },
  { icon: Cpu, label: "Gemma local ou na nuvem" },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } },
};

export function Hero({ isAuthenticated, onSignIn }: SignInProps) {
  return (
    <section id="topo" className="relative px-5 pt-32 pb-20 sm:pt-40 sm:pb-28">
      <HeroBackground />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative mx-auto flex max-w-4xl flex-col items-center text-center"
      >
        <motion.p
          variants={item}
          className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium tracking-wide text-violet-200"
        >
          <Sparkles className="size-3.5 text-violet-400" aria-hidden="true" />
          AI Residence Challenge
        </motion.p>

        <motion.h1
          variants={item}
          className="mt-6 font-display text-4xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-6xl lg:text-7xl"
        >
          Pare de adiar. <span className="text-gradient">Destrave</span> seus projetos.
        </motion.h1>

        <motion.p
          variants={item}
          className="mt-6 max-w-2xl text-base leading-relaxed text-pretty text-muted sm:text-lg"
        >
          Conte ao Destrava qual é a meta e quanto tempo você tem. Agentes de IA dividem o
          trabalho em blocos de foco, encaixam tudo nos horários livres do seu Google Agenda e
          replanejam quando a semana muda.
        </motion.p>

        <motion.div variants={item} className="mt-9 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
          <Button
            size="lg"
            onClick={onSignIn}
            className="w-full sm:w-auto"
            icon={
              isAuthenticated ? undefined : (
                <span className="grid size-7 place-items-center rounded-full bg-white">
                  <GoogleIcon className="size-4" />
                </span>
              )
            }
          >
            {isAuthenticated ? (
              <>
                Abrir o chat <ArrowRight className="size-4" aria-hidden="true" />
              </>
            ) : (
              "Entrar com o Google"
            )}
          </Button>
          <a
            href="#capacidades"
            className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-purple-500/25 bg-white/5 px-6 text-[0.95rem] font-medium transition hover:border-purple-400/50 hover:bg-white/10 sm:w-auto"
          >
            Ver como funciona <ArrowDown className="size-4" aria-hidden="true" />
          </a>
        </motion.div>

        <motion.ul variants={item} className="mt-10 flex flex-wrap justify-center gap-2.5" aria-label="Destaques do projeto">
          {BADGES.map(({ icon: Icon, label }) => (
            <li
              key={label}
              className="inline-flex items-center gap-2 rounded-full border border-purple-500/20 bg-ink-900/70 px-3.5 py-1.5 text-xs text-slate-300 transition hover:border-purple-400/50 hover:text-white"
            >
              <Icon className="size-3.5 text-violet-400" aria-hidden="true" />
              {label}
            </li>
          ))}
        </motion.ul>
      </motion.div>

      <ChatPreview />
    </section>
  );
}

function HeroBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_70%_60%_at_50%_30%,black,transparent)]" />
      <div className="animate-pulse-glow absolute top-[-14rem] left-1/2 size-[44rem] -translate-x-1/2 rounded-full bg-violet-700/30 blur-[130px]" />
      <div className="animate-drift absolute top-40 left-[8%] size-72 rounded-full bg-purple-500/15 blur-[100px]" />
      <div className="animate-drift absolute top-72 right-[6%] size-80 rounded-full bg-violet-600/15 blur-[110px] [animation-delay:-6s]" />
    </div>
  );
}

/** Static mock of a chat turn, so visitors see the product before signing in. */
function ChatPreview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 48 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, delay: 0.55, ease: [0.22, 1, 0.36, 1] }}
      className="relative mx-auto mt-16 max-w-3xl sm:mt-20"
      aria-hidden="true"
    >
      <div className="absolute -inset-x-10 -bottom-10 top-10 rounded-[3rem] bg-violet-600/20 blur-3xl" />
      <div className="glass glow relative rounded-3xl p-2">
        <div className="flex items-center gap-1.5 px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="size-2.5 rounded-full bg-white/15" />
          <span className="ml-3 text-xs text-muted">Destrava · Chat</span>
        </div>
        <div className="space-y-4 rounded-2xl bg-ink-950/80 p-4 text-left sm:p-6">
          <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-violet-600 to-violet-800 px-4 py-2.5 text-sm">
            Monte um plano para eu fazer meu TCC, tenho 10 horas livres esta semana
          </div>
          <div className="flex gap-3">
            <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-violet-800">
              <Sparkles className="size-4" />
            </span>
            <div className="min-w-0 flex-1 space-y-3">
              <p className="text-sm leading-relaxed text-slate-200">
                Bora destravar <strong className="text-white">TCC</strong>! Dividi as suas 10 horas
                em 5 blocos de foco.
              </p>
              <div className="max-w-md overflow-hidden rounded-2xl border border-purple-500/25 bg-ink-900">
                <p className="flex items-center gap-2 border-b border-purple-500/15 px-4 py-3 font-display text-sm font-semibold">
                  <CalendarCheck2 className="size-4 text-violet-300" /> Plano: TCC
                  <span className="ml-auto text-xs font-normal text-emerald-300">
                    5 blocos criados
                  </span>
                </p>
                {[
                  ["Escopo e roteiro", "Seg · 19:00 – 21:00"],
                  ["Pesquisa e referências", "Ter · 19:00 – 21:00"],
                  ["Desenvolvimento", "Qua · 19:00 – 21:00"],
                ].map(([phase, when]) => (
                  <p
                    key={phase}
                    className="flex items-center gap-3 border-b border-purple-500/10 px-4 py-2 text-xs last:border-0"
                  >
                    <Clock className="size-3.5 shrink-0 text-violet-400" />
                    <span className="flex-1 text-slate-200">{phase}</span>
                    <span className="text-muted tabular-nums">{when}</span>
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
