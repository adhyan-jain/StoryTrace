"use client";

import { useState } from "react";

export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  // Positioned from the cursor's actual viewport coordinates (position:
  // fixed) rather than CSS-anchored to the trigger element. The trigger
  // (a <mark> inside wrapped paragraph text) is `inline`, and when the
  // highlighted phrase itself wraps across a line break, an absolutely
  // positioned child of an inline element gets fragmented across each of
  // its line boxes -- it rendered as a garbled overlap straddling both
  // lines instead of one tooltip near the hovered line. Tracking the
  // cursor sidesteps that entirely: there's exactly one cursor position,
  // regardless of how many line fragments the trigger spans.
  function updatePosition(e: React.MouseEvent) {
    setPos({ top: e.clientY, left: e.clientX });
  }

  return (
    <span
      className="relative inline"
      onMouseEnter={updatePosition}
      onMouseMove={updatePosition}
      onMouseLeave={() => setPos(null)}
    >
      {children}
      {pos && (
        <span
          className="fixed z-50 w-max max-w-xs px-3 py-2 border border-[var(--bg-border)] bg-[var(--bg-elevated)] text-[11px] font-[family-name:var(--font-mono)] text-[var(--text-primary)] shadow-none pointer-events-none"
          style={{ top: pos.top - 12, left: pos.left, transform: "translate(-50%, -100%)" }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
