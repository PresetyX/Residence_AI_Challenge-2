"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Cloud, Cpu } from "lucide-react";
import { type KeyboardEvent, useId, useRef, useState } from "react";
import { useDismiss } from "@/hooks/use-dismiss";
import { MODELS, getModel } from "@/lib/models";
import type { ModelRuntime } from "@/lib/types";
import { useChatStore } from "@/store/chat-store";

const RUNTIME_ICON: Record<ModelRuntime, typeof Cpu> = { local: Cpu, cloud: Cloud };

export function ModelSelector() {
  const selectedModelId = useChatStore((state) => state.selectedModelId);
  const selectModel = useChatStore((state) => state.selectModel);
  const isGenerating = useChatStore((state) => state.isGenerating);

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const baseId = useId();

  const selected = getModel(selectedModelId);
  const SelectedIcon = RUNTIME_ICON[selected.runtime];

  const close = (restoreFocus = true) => {
    setOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  };
  useDismiss(rootRef, open, () => close(false));

  function openList() {
    setActiveIndex(MODELS.findIndex((model) => model.id === selectedModelId));
    setOpen(true);
    requestAnimationFrame(() => listRef.current?.focus());
  }

  function choose(index: number) {
    selectModel(MODELS[index].id);
    close();
  }

  function onListKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActiveIndex((index) => (index + 1) % MODELS.length);
        break;
      case "ArrowUp":
        event.preventDefault();
        setActiveIndex((index) => (index - 1 + MODELS.length) % MODELS.length);
        break;
      case "Home":
        event.preventDefault();
        setActiveIndex(0);
        break;
      case "End":
        event.preventDefault();
        setActiveIndex(MODELS.length - 1);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        choose(activeIndex);
        break;
      case "Tab":
        close(false);
        break;
    }
  }

  return (
    <div ref={rootRef} className="relative min-w-0">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Modelo de IA: ${selected.name}. ${selected.description}`}
        disabled={isGenerating}
        onClick={() => (open ? close() : openList())}
        onKeyDown={(event) => {
          if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            event.preventDefault();
            openList();
          }
        }}
        className={`flex h-10 max-w-full items-center gap-2.5 rounded-xl border px-3 text-left transition disabled:opacity-60 ${
          open
            ? "border-violet-400/70 bg-violet-600/15 shadow-[0_0_24px_-6px_rgb(124_58_237/0.8)]"
            : "border-purple-500/25 bg-white/5 hover:border-purple-400/50 hover:bg-white/10"
        }`}
      >
        <SelectedIcon className="size-4 shrink-0 text-violet-300" aria-hidden="true" />
        <span className="min-w-0">
          <span className="block truncate text-sm leading-tight font-medium">
            {selected.shortName}
          </span>
          <span className="hidden truncate text-[0.68rem] leading-tight text-muted sm:block">
            {selected.description}
          </span>
        </span>
        <ChevronDown
          aria-hidden="true"
          className={`size-4 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            className="glass glow fixed inset-x-3 top-[4.25rem] z-50 origin-top rounded-2xl p-1.5 sm:absolute sm:inset-x-auto sm:top-full sm:left-0 sm:mt-2 sm:w-[26rem]"
          >
            <p id={`${baseId}-label`} className="px-3 pt-2 pb-1.5 text-xs font-medium text-muted">
              Escolha o modelo de IA
            </p>
            <ul
              ref={listRef}
              role="listbox"
              tabIndex={-1}
              aria-labelledby={`${baseId}-label`}
              aria-activedescendant={`${baseId}-option-${activeIndex}`}
              onKeyDown={onListKeyDown}
              className="space-y-0.5 outline-none"
            >
              {MODELS.map((model, index) => {
                const Icon = RUNTIME_ICON[model.runtime];
                const isSelected = model.id === selectedModelId;
                const isActive = index === activeIndex;
                return (
                  <li
                    key={model.id}
                    id={`${baseId}-option-${index}`}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => choose(index)}
                    onPointerMove={() => setActiveIndex(index)}
                    className={`flex items-start gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                      isActive ? "bg-violet-600/20" : ""
                    }`}
                  >
                    <span
                      className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border ${
                        isSelected
                          ? "border-violet-300/60 bg-violet-600 text-white"
                          : "border-purple-500/25 bg-ink-950/60 text-violet-300"
                      }`}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-white">{model.name}</span>
                      <span className="mt-0.5 block text-xs text-muted">{model.description}</span>
                    </span>
                    {isSelected && (
                      <Check className="mt-1.5 size-4 shrink-0 text-violet-300" aria-hidden="true" />
                    )}
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
