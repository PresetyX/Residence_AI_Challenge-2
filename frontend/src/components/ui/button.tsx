import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition duration-200 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-gradient-to-b from-violet-400 to-violet-500 text-ink-950 shadow-[0_8px_30px_-8px_rgb(189_147_249/0.8)] hover:from-violet-300 hover:to-violet-400 hover:shadow-[0_8px_36px_-6px_rgb(189_147_249/0.9)]",
  secondary:
    "border border-purple-500/25 bg-white/5 text-white hover:border-purple-400/50 hover:bg-white/10",
  ghost: "text-muted hover:bg-white/8 hover:text-white",
  danger:
    "bg-gradient-to-b from-red-400 to-red-500 text-ink-950 shadow-[0_8px_30px_-10px_rgb(255_85_85/0.8)] hover:from-red-300 hover:to-red-400",
};

const SIZES: Record<Size, string> = {
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-[0.95rem]",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}
