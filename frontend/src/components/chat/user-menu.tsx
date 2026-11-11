"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CalendarCheck2, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useDismiss } from "@/hooks/use-dismiss";
import { getInitials } from "@/lib/format";
import type { User } from "@/lib/types";
import { useAuthStore } from "@/store/auth-store";
import { useCalendarStore } from "@/store/calendar-store";
import { useChatStore } from "@/store/chat-store";
import { useUiStore } from "@/store/ui-store";
import { resetMockCalendar } from "@/services/calendar-service";
import { resetMockSupervisor } from "@/services/mocks/mock-supervisor";

export function Avatar({ user, size = "size-9" }: { user: User; size?: string }) {
  if (user.avatarUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- remote Google avatar, no optimization needed
      <img
        src={user.avatarUrl}
        alt=""
        referrerPolicy="no-referrer"
        className={`${size} shrink-0 rounded-full object-cover ring-1 ring-purple-400/40`}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={`${size} grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-violet-400 to-violet-700 text-xs font-semibold ring-1 ring-purple-300/40`}
    >
      {getInitials(user.name)}
    </span>
  );
}

export function UserMenu({ user }: { user: User }) {
  const router = useRouter();
  const signOut = useAuthStore((state) => state.signOut);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useDismiss(rootRef, open, () => setOpen(false));

  async function handleSignOut() {
    setOpen(false);
    useChatStore.getState().resetConversation();
    useUiStore.getState().closePanel();
    useCalendarStore.getState().reset();
    resetMockCalendar();
    resetMockSupervisor();
    await signOut();
    router.replace("/");
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Conta de ${user.name}`}
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2.5 rounded-full p-0.5 transition hover:bg-white/5 lg:pr-3"
      >
        <Avatar user={user} />
        <span className="hidden min-w-0 text-left lg:block">
          <span className="block max-w-40 truncate text-sm leading-tight font-medium">
            {user.name}
          </span>
          <span className="block max-w-40 truncate text-xs leading-tight text-muted">
            {user.email}
          </span>
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            aria-label="Conta"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            className="glass glow absolute right-0 z-50 mt-2 w-72 origin-top-right rounded-2xl p-1.5"
          >
            <div className="flex items-center gap-3 px-3 py-3">
              <Avatar user={user} size="size-10" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user.name}</p>
                <p className="truncate text-xs text-muted">{user.email}</p>
              </div>
            </div>
            <p className="mx-1.5 mb-1.5 flex items-center gap-2 rounded-xl bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
              <CalendarCheck2 className="size-3.5 shrink-0" aria-hidden="true" />
              Google Agenda conectado (leitura e escrita)
            </p>
            <button
              type="button"
              role="menuitem"
              onClick={handleSignOut}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-200 transition hover:bg-white/8 hover:text-white"
            >
              <LogOut className="size-4 text-muted" aria-hidden="true" />
              Sair da conta
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
