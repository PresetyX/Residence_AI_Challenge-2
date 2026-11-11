"use client";

import { motion } from "framer-motion";
import { CalendarPlus, CircleAlert, Sparkles } from "lucide-react";
import { memo } from "react";
import { formatTime } from "@/lib/format";
import { getModel } from "@/lib/models";
import type { ChatMessage } from "@/lib/types";
import { useUiStore } from "@/store/ui-store";
import { CalendarEventCard } from "./calendar-event-card";
import { CalendarPlanCard } from "./calendar-plan-card";
import { Markdown } from "./markdown";
import { ProjectPlanCard } from "./project-plan-card";

export const MessageBubble = memo(function MessageBubble({ message }: { message: ChatMessage }) {
  return message.role === "user" ? (
    <UserMessage message={message} />
  ) : (
    <AssistantMessage message={message} />
  );
});

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <motion.li
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex flex-col items-end"
    >
      <span className="sr-only">Você disse:</span>
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-violet-600 to-violet-800 px-4 py-2.5 text-[0.9375rem] leading-relaxed break-words whitespace-pre-wrap shadow-[0_8px_30px_-12px_rgb(124_58_237/0.9)] sm:max-w-[75%]">
        {message.content}
      </div>
      <time dateTime={message.createdAt} className="mt-1 mr-1 text-[0.68rem] text-slate-500">
        {formatTime(message.createdAt)}
      </time>
    </motion.li>
  );
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  const isStreaming = message.status === "streaming";
  const isThinking = isStreaming && message.content === "";
  const isError = message.status === "error";
  const actions = message.calendarActions ?? [];
  const openCreateForm = useUiStore((state) => state.openCreateForm);

  return (
    <motion.li
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex gap-3"
    >
      <span
        aria-hidden="true"
        className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-violet-800 ${
          isStreaming ? "animate-pulse shadow-[0_0_22px_rgb(124_58_237/0.9)]" : ""
        }`}
      >
        <Sparkles className="size-4" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="mb-1.5 flex flex-wrap items-baseline gap-x-2 text-xs text-muted">
          <span className="font-medium text-violet-200">Destrava</span>
          {message.modelId && <span>{getModel(message.modelId).shortName}</span>}
          <time dateTime={message.createdAt} className="text-slate-500">
            {formatTime(message.createdAt)}
          </time>
        </p>

        {isThinking ? (
          <ThinkingDots label={message.statusText} />
        ) : isError ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3.5 py-3 text-sm text-red-200"
          >
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {message.content}
          </p>
        ) : (
          <div className="text-slate-200">
            <Markdown content={message.content} />
            {isStreaming && (
              <span
                aria-hidden="true"
                className="animate-blink mt-1 inline-block h-4 w-2 rounded-sm bg-violet-400"
              />
            )}
          </div>
        )}

        {actions.length === 1 && (
          <div className="mt-4">
            <CalendarEventCard action={actions[0]} />
          </div>
        )}
        {actions.length > 1 && (
          <div className="mt-4">
            <CalendarPlanCard actions={actions} />
          </div>
        )}

        {message.projectPlan && (
          <div className="mt-4">
            <ProjectPlanCard plan={message.projectPlan} />
          </div>
        )}

        {message.suggestsManualPanel && message.status === "done" && (
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={openCreateForm}
              aria-haspopup="dialog"
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-purple-500/30 bg-violet-600/10 px-3.5 text-sm font-medium text-violet-100 transition hover:border-violet-400/70 hover:bg-violet-600/25 hover:text-white"
            >
              <CalendarPlus className="size-4" aria-hidden="true" />
              Abrir painel manual
            </button>
          </div>
        )}
      </div>
    </motion.li>
  );
}

function ThinkingDots({ label }: { label?: string }) {
  return (
    <p className="flex min-h-7 items-center gap-1.5" role="status">
      <span className="sr-only">{label ?? "O assistente está pensando…"}</span>
      {[0, 1, 2].map((index) => (
        <motion.span
          key={index}
          aria-hidden="true"
          className="size-2 rounded-full bg-violet-400"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: index * 0.16 }}
        />
      ))}
      {label && (
        <span aria-hidden="true" className="ml-2 text-sm text-muted">
          {label}
        </span>
      )}
    </p>
  );
}
