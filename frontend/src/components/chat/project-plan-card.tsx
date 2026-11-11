"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Flag, ListChecks } from "lucide-react";
import { useId, useState } from "react";
import { formatShortDate } from "@/lib/format";
import type { ProjectPlan, ProjectTask } from "@/lib/types";

/** Inline card for a project plan returned by the backend planner. */
export function ProjectPlanCard({ plan }: { plan: ProjectPlan }) {
  const total = plan.tasks.reduce((sum, task) => sum + task.storyPoints, 0);
  const max = Math.max(...plan.tasks.map((task) => task.storyPoints), 1);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      aria-label={`Plano do projeto em ${plan.tasks.length} etapas`}
      className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-purple-500/25 bg-ink-900/80 shadow-[0_10px_40px_-20px_rgb(124_58_237/0.7)] backdrop-blur"
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-400 to-violet-700"
      />
      <header className="flex items-center gap-3 border-b border-purple-500/15 py-3.5 pr-4 pl-5">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-violet-600/20 text-violet-300">
          <ListChecks className="size-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-display font-semibold">Plano do projeto</p>
          <p className="flex items-center gap-1 text-xs text-muted">
            <Flag className="size-3" aria-hidden="true" />
            Prazo {formatShortDate(`${plan.deadline}T12:00:00`)}
            <span aria-hidden="true"> · </span>
            {plan.tasks.length} etapas
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="font-display text-lg leading-none font-semibold tabular-nums text-violet-200">
            {total}
          </p>
          <p className="text-[0.68rem] text-muted">story points</p>
        </div>
      </header>
      <ol className="divide-y divide-purple-500/10">
        {plan.tasks.map((task) => (
          <TaskRow key={task.step} task={task} max={max} />
        ))}
      </ol>
    </motion.article>
  );
}

function TaskRow({ task, max }: { task: ProjectTask; max: number }) {
  const [open, setOpen] = useState(false);
  const detailsId = useId();

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={detailsId}
        className="flex w-full items-center gap-3 py-2.5 pr-3 pl-5 text-left transition-colors hover:bg-violet-600/10"
      >
        <span className="grid size-6 shrink-0 place-items-center rounded-md bg-violet-600/20 text-xs font-semibold text-violet-200 tabular-nums">
          {task.step}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-white">{task.title}</span>
          <span className="mt-1 block h-1 overflow-hidden rounded-full bg-violet-950/70" aria-hidden="true">
            <span
              className="block h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-400"
              style={{ width: `${(task.storyPoints / max) * 100}%` }}
            />
          </span>
        </span>
        <span className="shrink-0 rounded-full bg-violet-500/10 px-2 py-0.5 text-[0.68rem] font-medium text-violet-200 tabular-nums">
          {task.storyPoints} SP
        </span>
        <ChevronDown
          className={`size-4 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.dl
            id={detailsId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-2 overflow-hidden pr-4 pb-3 pl-14 text-sm"
          >
            <Detail label="Objetivo" value={task.goal} />
            <Detail label="Entregáveis" value={task.deliverables} />
            <Detail label="Demonstração" value={task.demo} />
            <Detail
              label="Depende de"
              value={task.dependsOn > 0 ? `Etapa ${task.dependsOn}` : "Nenhuma etapa: pode começar já"}
            />
          </motion.dl>
        )}
      </AnimatePresence>
    </li>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[0.68rem] font-medium tracking-wide text-violet-300/80 uppercase">{label}</dt>
      <dd className="mt-0.5 text-slate-300">{value}</dd>
    </div>
  );
}
