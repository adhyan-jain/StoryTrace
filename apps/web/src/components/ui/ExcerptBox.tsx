import clsx from "clsx";

export function ExcerptBox({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={clsx(
        "font-[family-name:var(--font-mono)] text-[12px] leading-relaxed text-[var(--text-secondary)] bg-[var(--bg-elevated)] border border-[var(--bg-border)] rounded-md px-3 py-2 whitespace-pre-wrap break-words",
        className,
      )}
    >
      {children}
    </div>
  );
}
