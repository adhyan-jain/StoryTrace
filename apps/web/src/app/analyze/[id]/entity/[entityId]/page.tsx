"use client";

import { useParams } from "next/navigation";
import { TimelinePage } from "@/components/EntityTimeline/TimelinePage";

export default function EntityTimelineRoute() {
  const { id, entityId } = useParams<{ id: string; entityId: string }>();
  return <TimelinePage id={id} entityId={entityId} />;
}
