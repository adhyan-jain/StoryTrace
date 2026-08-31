"use client";

import { useState } from "react";

export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      className="relative inline"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-max max-w-xs px-3 py-2 rounded-md border border-[var(--bg-border)] bg-[var(--bg-elevated)] text-[11px] font-[family-name:var(--font-mono)] text-[var(--text-primary)] shadow-none pointer-events-none"
        >
          {content}
        </span>
      )}
    </span>
  );
}
