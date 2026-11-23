"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chat-store";
import { EmptyState } from "./empty-state";
import { MessageBubble } from "./message-bubble";

/** Distance from the bottom (px) within which new content keeps the view pinned. */
const STICK_THRESHOLD = 120;

export function MessageList({ userFirstName }: { userFirstName: string }) {
  const messages = useChatStore((state) => state.messages);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    const element = scrollRef.current;
    element?.scrollTo({ top: element.scrollHeight, behavior });
  }, []);

  const onScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    const distance = element.scrollHeight - element.scrollTop - element.clientHeight;
    // Reaching the bottom re-pins. Unpinning only happens on explicit user input
    // (see `unpin` below): scroll events alone also fire for our own scrolling.
    if (distance < STICK_THRESHOLD) pinnedRef.current = true;
    setShowJump(!pinnedRef.current && distance > STICK_THRESHOLD * 2);
  }, []);

  /** The user took over scrolling (wheel up, touch drag, keyboard, scrollbar). */
  const unpin = useCallback(() => {
    pinnedRef.current = false;
  }, []);

  const lastMessage = messages[messages.length - 1];
  const messageCount = messages.length;

  // A new message always scrolls into view, smoothly.
  useEffect(() => {
    pinnedRef.current = true;
    scrollToBottom("smooth");
  }, [messageCount, scrollToBottom]);

  // While tokens stream in, follow along only if the user has not scrolled up.
  useEffect(() => {
    if (pinnedRef.current) scrollToBottom("auto");
  }, [lastMessage?.content, lastMessage?.calendarActions, lastMessage?.suggestsManualPanel, scrollToBottom]);

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollRef}
        onScroll={onScroll}
        onWheel={(event) => event.deltaY < 0 && unpin()}
        onTouchMove={unpin}
        onKeyDown={(event) =>
          ["ArrowUp", "PageUp", "Home"].includes(event.key) && unpin()
        }
        onPointerDown={(event) => event.target === event.currentTarget && unpin()}
        className="h-full overflow-y-auto px-4 sm:px-6"
      >
        {messages.length === 0 ? (
          <EmptyState userFirstName={userFirstName} />
        ) : (
          <ol
            role="log"
            aria-label="Conversa com o assistente"
            aria-live="polite"
            aria-relevant="additions"
            className="mx-auto flex max-w-3xl flex-col gap-7 py-8"
          >
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </ol>
        )}
      </div>

      <AnimatePresence>
        {showJump && (
          <motion.button
            type="button"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={() => {
              pinnedRef.current = true;
              scrollToBottom("smooth");
            }}
            aria-label="Ir para o fim da conversa"
            className="glass absolute bottom-3 left-1/2 grid size-9 -translate-x-1/2 place-items-center rounded-full text-violet-200 shadow-lg transition-colors hover:text-white"
          >
            <ArrowDown className="size-4" aria-hidden="true" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
