"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Ellipsis, Pencil, Trash2, X } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { useDismiss } from "@/hooks/use-dismiss";
import { useCalendarStore } from "@/store/calendar-store";
import { type PanelView, useUiStore } from "@/store/ui-store";
import { AgendaList } from "./agenda-list";
import { DeleteEventModal } from "./delete-event-modal";
import { EventDetails } from "./event-details";
import { EventForm } from "./event-form";

const TITLES: Record<Exclude<PanelView, "closed">, string> = {
  list: "Agenda",
  create: "Novo agendamento",
  details: "Detalhes do agendamento",
  edit: "Editar agendamento",
};

/**
 * The Agenda panel: the user's manual control over the calendar. It lists events,
 * creates new ones, and shows / edits / deletes a selected event.
 */
export function EventSidebar() {
  const view = useUiStore((state) => state.panelView);
  const activeEventId = useUiStore((state) => state.activeEventId);
  const isDeleteModalOpen = useUiStore((state) => state.isDeleteModalOpen);
  const close = useUiStore((state) => state.closePanel);
  const goBack = useUiStore((state) => state.goBack);
  const editActiveEvent = useUiStore((state) => state.editActiveEvent);
  const openEventDetails = useUiStore((state) => state.openEventDetails);
  const setDeleteModalOpen = useUiStore((state) => state.setDeleteModalOpen);

  const event = useCalendarStore((state) =>
    activeEventId && !state.deletedIds[activeEventId] ? state.events[activeEventId] : undefined,
  );

  const panelRef = useRef<HTMLElement>(null);
  const isOpen = view !== "closed";
  const needsEvent = view === "details" || view === "edit";

  // The event can disappear while it is open (e.g. the AI clears its plan).
  useEffect(() => {
    if (needsEvent && !event) goBack();
  }, [needsEvent, event, goBack]);

  // Move focus into the drawer on open and give it back on close.
  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const frame = requestAnimationFrame(() => {
      if (!panelRef.current?.contains(document.activeElement)) panelRef.current?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || isDeleteModalOpen) return;
    const onKeyDown = (keyEvent: globalThis.KeyboardEvent) => {
      if (keyEvent.key !== "Escape") return;
      if (view === "edit" || view === "create") goBack();
      else close();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, isDeleteModalOpen, view, goBack, close]);

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              key="backdrop"
              aria-hidden="true"
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={close}
            />
            <motion.aside
              key="panel"
              ref={panelRef}
              role="dialog"
              aria-label={TITLES[view]}
              tabIndex={-1}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 330, damping: 36 }}
              className="glass fixed inset-y-0 right-0 z-40 flex w-full flex-col border-y-0 border-r-0 outline-none sm:w-[26rem] lg:top-16 lg:z-20"
            >
              <header className="flex h-16 shrink-0 items-center gap-1 border-b border-purple-500/15 px-3">
                {view !== "list" && (
                  <button
                    type="button"
                    onClick={goBack}
                    aria-label={view === "edit" ? "Voltar aos detalhes" : "Voltar à agenda"}
                    className="grid size-9 place-items-center rounded-full text-muted transition hover:bg-white/10 hover:text-white"
                  >
                    <ArrowLeft className="size-4.5" aria-hidden="true" />
                  </button>
                )}
                <h2
                  className={`min-w-0 flex-1 truncate font-display font-semibold ${view === "list" ? "pl-2" : "pl-1"}`}
                >
                  {TITLES[view]}
                </h2>
                {view === "details" && event && (
                  <ActionsMenu
                    onEdit={editActiveEvent}
                    onDelete={() => setDeleteModalOpen(true)}
                  />
                )}
                <button
                  type="button"
                  onClick={close}
                  aria-label="Fechar painel"
                  className="grid size-9 place-items-center rounded-full text-muted transition hover:bg-white/10 hover:text-white"
                >
                  <X className="size-4.5" aria-hidden="true" />
                </button>
              </header>

              <div className="min-h-0 flex-1 overflow-y-auto">
                <AnimatePresence mode="wait" initial={false}>
                  <motion.div
                    key={`${view}-${activeEventId ?? ""}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.18 }}
                    className="p-5"
                  >
                    {view === "list" && <AgendaList />}
                    {view === "create" && (
                      <EventForm onCancel={goBack} onSaved={openEventDetails} />
                    )}
                    {view === "details" && event && <EventDetails event={event} />}
                    {view === "edit" && event && (
                      <EventForm event={event} onCancel={goBack} onSaved={openEventDetails} />
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {event && (
        <DeleteEventModal
          event={event}
          open={isDeleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
        />
      )}
    </>
  );
}

/** The "..." contextual menu in the drawer header. */
function ActionsMenu({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useDismiss(rootRef, open, () => {
    setOpen(false);
    buttonRef.current?.focus();
  });

  useEffect(() => {
    if (open) menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [open]);

  function onMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = [...(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
    const index = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      items[(index + 1) % items.length]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      items[(index - 1 + items.length) % items.length]?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  const run = (action: () => void) => () => {
    setOpen(false);
    action();
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Ações do agendamento"
        title="Ações do agendamento"
        onClick={() => setOpen((value) => !value)}
        className={`grid size-9 place-items-center rounded-full transition hover:bg-white/10 hover:text-white ${
          open ? "bg-violet-600/25 text-white" : "text-muted"
        }`}
      >
        <Ellipsis className="size-5" aria-hidden="true" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            ref={menuRef}
            role="menu"
            aria-label="Ações do agendamento"
            onKeyDown={onMenuKeyDown}
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.14 }}
            className="glass glow absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-2xl p-1.5"
          >
            <button
              type="button"
              role="menuitem"
              onClick={run(onEdit)}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-100 transition hover:bg-white/8 focus-visible:bg-white/8"
            >
              <Pencil className="size-4 text-violet-300" aria-hidden="true" />
              Editar agendamento
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={run(onDelete)}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-red-300 transition hover:bg-red-500/15 focus-visible:bg-red-500/15"
            >
              <Trash2 className="size-4" aria-hidden="true" />
              Excluir agendamento
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
