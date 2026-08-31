"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DropZone } from "@/components/Upload/DropZone";

export default function Home() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const activeId = localStorage.getItem("storytrace_active_id");
    if (activeId) {
      router.replace(`/analyze/${activeId}`);
    } else {
      setChecked(true);
    }
  }, [router]);

  if (!checked) return null;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-12 bg-[var(--bg-base)] px-6">
      <div className="text-center">
        <h1 className="text-3xl font-semibold text-[var(--text-primary)] tracking-tight">StoryTrace</h1>
        <p className="text-[var(--text-secondary)] text-sm mt-2">Narrative continuity intelligence.</p>
      </div>
      <DropZone />
    </div>
  );
}
