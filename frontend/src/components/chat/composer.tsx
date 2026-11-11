"use client";

import { ArrowUp, Square } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { getModel } from "@/lib/models";
import { useChatStore } from "@/store/chat-store";

const MAX_HEIGHT_PX = 200;

export function Composer() {
  const sendMessage = useChatStore((state) => state.sendMessage);
  const stopGenerating = useChatStore((state) => state.stopGenerating);
  const isGenerating = useChatStore((state) => state.isGenerating);
  const model = useChatStore((state) => getModel(state.selectedModelId));

  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !isGenerating;

  // Grow with the content up to MAX_HEIGHT_PX, then scroll.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  function submit() {
    if (!canSend) return;
    void sendMessage(value);
    setValue("");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="shrink-0 px-3 pt-2 pb-3 sm:px-6 sm:pb-4">
      <form
        onSubmit={onSubmit}
        className="glass mx-auto flex max-w-3xl items-end gap-2 rounded-3xl p-2 pl-4 transition focus-within:border-violet-400/60 focus-within:shadow-[0_0_40px_-10px_rgb(124_58_237/0.8)]"
      >
        <label htmlFor="chat-input" className="sr-only">
          Mensagem para o assistente
        </label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Peça algo ao Destrava…"
          aria-describedby="chat-input-hint"
          className="min-h-10 flex-1 resize-none bg-transparent py-2 text-[0.9375rem] leading-relaxed text-white outline-none placeholder:text-slate-500"
        />
        {isGenerating ? (
          <button
            type="button"
            onClick={stopGenerating}
            aria-label="Interromper resposta"
            title="Interromper resposta"
            className="grid size-10 shrink-0 place-items-center rounded-full border border-purple-400/40 bg-white/10 transition hover:bg-white/20"
          >
            <Square className="size-3.5 fill-current" aria-hidden="true" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Enviar mensagem"
            title="Enviar mensagem"
            className="grid size-10 shrink-0 place-items-center rounded-full bg-gradient-to-b from-violet-500 to-violet-700 shadow-[0_0_24px_-4px_rgb(124_58_237/0.9)] transition hover:from-violet-400 hover:to-violet-600 active:scale-95 disabled:pointer-events-none disabled:from-white/10 disabled:to-white/10 disabled:text-slate-500 disabled:shadow-none"
          >
            <ArrowUp className="size-4.5" aria-hidden="true" />
          </button>
        )}
      </form>
      <p id="chat-input-hint" className="mx-auto mt-2 max-w-3xl text-center text-xs text-slate-500">
        <span className="hidden sm:inline">Enter envia, Shift + Enter quebra a linha. </span>
        Respondendo com {model.shortName}. A IA pode errar: confira seus agendamentos.
      </p>
    </div>
  );
}
