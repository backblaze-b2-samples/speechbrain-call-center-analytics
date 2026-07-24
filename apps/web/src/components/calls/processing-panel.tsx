"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

import { Progress } from "@/components/ui/progress";
import type { PipelineStage } from "@speechbrain-call-center-analytics/shared";

// The four pipeline stages, in the order the backend records them into
// meta.json (segmentation -> transcription -> diarization -> analytics).
const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "segmentation", label: "Voice-activity segmentation" },
  { key: "transcription", label: "ASR transcription" },
  { key: "diarization", label: "Speaker diarization" },
  { key: "analytics", label: "Emotion & sentiment" },
];

/**
 * Shown in the Transcript/Analytics tab bodies while a call is `processing`, in
 * place of the idle "Run analysis" empty state. The advancing indicator is
 * driven by the real `stage` the backend writes as each stage begins — the bar
 * reflects stages actually completed, not a fabricated timer.
 */
export function ProcessingPanel({ stage }: { stage: PipelineStage | null }) {
  // Which stage is in flight. Default to the first stage for the brief window
  // before the backend has recorded one.
  const foundIndex = STAGES.findIndex((s) => s.key === stage);
  const currentIndex = foundIndex === -1 ? 0 : foundIndex;
  const percent = (currentIndex / STAGES.length) * 100;

  return (
    <div className="rounded-lg border border-border bg-muted/20 p-6">
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--chart-1)]" />
        <div>
          <p className="text-sm font-semibold">Analyzing recording…</p>
          <p className="text-xs text-muted-foreground">
            Step {currentIndex + 1} of {STAGES.length} · runs locally on CPU, so
            a cold run can take a few minutes.
          </p>
        </div>
      </div>

      <Progress value={percent} className="mt-4" />

      <ol className="mt-5 space-y-2.5">
        {STAGES.map((s, i) => {
          const isDone = i < currentIndex;
          const isActive = i === currentIndex;
          return (
            <li key={s.key} className="flex items-center gap-2.5 text-sm">
              {isDone ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--success)]" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[var(--chart-1)]" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-muted-foreground/40" />
              )}
              <span
                className={
                  isActive
                    ? "font-medium"
                    : isDone
                      ? "text-muted-foreground"
                      : "text-muted-foreground/60"
                }
              >
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
