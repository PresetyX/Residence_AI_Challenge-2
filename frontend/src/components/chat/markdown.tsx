"use client";

import { Check, Copy } from "lucide-react";
import {
  type ComponentPropsWithoutRef,
  type ReactElement,
  isValidElement,
  memo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

function CodeBlock({ children, ...props }: ComponentPropsWithoutRef<"pre">) {
  const preRef = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const codeClass = isValidElement(children)
    ? ((children as ReactElement<{ className?: string }>).props.className ?? "")
    : "";
  const language = /language-([\w-]+)/.exec(codeClass)?.[1] ?? "texto";

  async function copy() {
    try {
      await navigator.clipboard.writeText(preRef.current?.innerText ?? "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard can be blocked by the browser; the code stays selectable.
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-purple-500/20 bg-ink-950">
      <div className="flex items-center justify-between border-b border-purple-500/15 bg-violet-600/10 py-1 pr-1.5 pl-4">
        <span className="font-mono text-xs text-violet-200">{language}</span>
        <button
          type="button"
          onClick={copy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted transition hover:bg-white/10 hover:text-white"
        >
          {copied ? (
            <Check className="size-3.5 text-emerald-300" aria-hidden="true" />
          ) : (
            <Copy className="size-3.5" aria-hidden="true" />
          )}
          <span aria-live="polite">{copied ? "Copiado" : "Copiar"}</span>
        </button>
      </div>
      <pre
        ref={preRef}
        tabIndex={0}
        className="overflow-x-auto p-4 font-mono text-[0.8125rem] leading-relaxed"
        {...props}
      >
        {children}
      </pre>
    </div>
  );
}

const COMPONENTS = {
  pre: CodeBlock,
  a: ({ children, ...props }: ComponentPropsWithoutRef<"a">) => (
    <a target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  ),
  table: (props: ComponentPropsWithoutRef<"table">) => (
    <div className="overflow-x-auto rounded-xl border border-purple-500/20">
      <table {...props} />
    </div>
  ),
};

export const Markdown = memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={COMPONENTS}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
