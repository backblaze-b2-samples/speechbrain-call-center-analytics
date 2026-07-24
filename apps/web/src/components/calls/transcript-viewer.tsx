"use client";

import { useMemo } from "react";
import { MessageSquare } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useCallTranscript } from "@/lib/queries";
import { ProcessingPanel } from "./processing-panel";
import type { PipelineStage } from "@speechbrain-call-center-analytics/shared";

const SPEAKER_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

function mmss(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function TranscriptViewer({
  callId,
  enabled,
  processing = false,
  stage = null,
}: {
  callId: string;
  enabled: boolean;
  processing?: boolean;
  stage?: PipelineStage | null;
}) {
  const { data: segments = [], isLoading, error, refetch } = useCallTranscript(
    callId,
    enabled,
  );

  // Stable color per speaker, by first appearance.
  const colorFor = useMemo(() => {
    const map = new Map<string, string>();
    for (const seg of segments) {
      if (!map.has(seg.speaker)) {
        map.set(seg.speaker, SPEAKER_COLORS[map.size % SPEAKER_COLORS.length]);
      }
    }
    return map;
  }, [segments]);

  if (processing) {
    return <ProcessingPanel stage={stage} />;
  }
  if (!enabled) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="No transcript yet"
        description="Run analysis to generate a timestamped, speaker-labeled transcript."
      />
    );
  }
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} title="Couldn't load transcript" onRetry={() => refetch()} />;
  }
  if (segments.length === 0) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="Transcript is empty"
        description="The pipeline found no speech in this recording."
      />
    );
  }

  return (
    <div className="space-y-3">
      {segments.map((seg, i) => {
        const color = colorFor.get(seg.speaker) ?? SPEAKER_COLORS[0];
        return (
          <div key={i} className="flex gap-3">
            <div className="w-14 shrink-0 pt-0.5 font-mono text-xs tabular-nums text-muted-foreground">
              {mmss(seg.start)}
            </div>
            <div
              className="flex-1 rounded-md border-l-2 bg-muted/30 px-3 py-2"
              style={{ borderColor: color }}
            >
              <div className="mb-0.5 flex items-center gap-2">
                <span className="text-xs font-semibold" style={{ color }}>
                  {seg.speaker}
                </span>
                {seg.emotion && (
                  <span className="rounded bg-background px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {seg.emotion}
                  </span>
                )}
              </div>
              <p className="text-sm text-pretty">{seg.text || <span className="text-muted-foreground italic">(no words)</span>}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
