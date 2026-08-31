"use client";

import clsx from "clsx";

export function TabBar<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly T[];
  active: T;
  onChange: (tab: T) => void;
}) {
  return (
    <div className="flex border-b border-[var(--bg-border)]">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={clsx(
            "px-3 py-2.5 text-xs font-semibold uppercase tracking-wider border-b-2 -mb-px transition-colors cursor-pointer",
            active === tab
              ? "text-[var(--text-primary)] border-[var(--accent-blue)]"
              : "text-[var(--text-muted)] border-transparent hover:text-[var(--text-secondary)]",
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
