export default function Loading() {
  return (
    <div className="flex h-screen bg-[var(--bg-base)]">
      <div className="w-[280px] border-r border-[var(--bg-border)] bg-[var(--bg-surface)]" />
      <div className="flex-1" />
      <div className="w-[360px] border-l border-[var(--bg-border)] bg-[var(--bg-surface)]" />
    </div>
  );
}
