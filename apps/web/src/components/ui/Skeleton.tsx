import clsx from "clsx";

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-md bg-[var(--bg-elevated)]", className)} />;
}

/** Matches the row shape used by the dashboard's project list and a
 * project's version list, so the loading state doesn't jump around once
 * real rows replace it. */
export function ListRowSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border border-[var(--bg-border)] bg-[var(--bg-surface)] px-4 py-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-2.5 h-2.5 rounded-full shrink-0" />
        <div className="flex flex-col gap-1.5">
          <Skeleton className="h-3.5 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <Skeleton className="h-3 w-16 hidden sm:block" />
    </div>
  );
}

export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: rows }).map((_, i) => (
        <ListRowSkeleton key={i} />
      ))}
    </div>
  );
}
