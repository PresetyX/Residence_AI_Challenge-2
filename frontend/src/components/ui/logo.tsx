type LogoSize = "sm" | "md" | "lg";

const MARK_SIZE: Record<LogoSize, string> = {
  sm: "h-8 sm:h-9",
  md: "h-9 sm:h-10",
  lg: "h-14 sm:h-16",
};

const TEXT_SIZE: Record<LogoSize, string> = {
  sm: "text-base sm:text-lg",
  md: "text-lg sm:text-xl",
  lg: "text-2xl",
};

/**
 * The Destrava emblem (circuit brain + open padlock). The artwork ships as a white
 * alpha mask (public/logo-mark.png) so it can be tinted with the brand gradient and
 * glow in CSS instead of baking colors into the image. See `.logo-mark` in globals.css.
 */
export function LogoMark({ className = "h-9" }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`logo-mark-glow inline-block aspect-[5/4] ${className}`}>
      <span className="logo-mark block size-full" />
    </span>
  );
}

export function Logo({
  size = "md",
  hideTextOnMobile = false,
}: {
  size?: LogoSize;
  hideTextOnMobile?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark className={MARK_SIZE[size]} />
      <span
        className={`font-display font-semibold tracking-[0.14em] uppercase ${TEXT_SIZE[size]} ${
          hideTextOnMobile ? "hidden sm:inline" : ""
        }`}
      >
        Destrava
      </span>
    </span>
  );
}
