"use client";

import { AlertTriangle, BarChart3 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { useCallAnalytics } from "@/lib/queries";
import { SentimentBadge } from "./call-badges";
import { ProcessingPanel } from "./processing-panel";
import type { PipelineStage } from "@speechbrain-call-center-analytics/shared";

const TALK_COLORS = [
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

export function AnalyticsPanel({
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
  const { data, isLoading, error } = useCallAnalytics(callId, enabled);

  if (processing) {
    return <ProcessingPanel stage={stage} />;
  }
  if (!enabled || error) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No analytics yet"
        description="Run analysis to compute sentiment, talk-time, and flagged phrases."
      />
    );
  }
  if (isLoading || !data) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  const totalTalk = Object.values(data.talk_time).reduce((a, b) => a + b, 0) || 1;
  const speakers = Object.entries(data.talk_time);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-md border border-border p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Sentiment
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <SentimentBadge label={data.sentiment_label} />
            <span className="text-sm tabular-nums text-muted-foreground">
              {data.sentiment_score.toFixed(2)}
            </span>
          </div>
        </div>
        <Metric label="Speakers" value={String(data.num_speakers)} />
        <Metric label="Silence ratio" value={`${Math.round(data.silence_ratio * 100)}%`} />
        <Metric label="Duration" value={mmss(data.duration_sec)} />
      </div>

      <Card>
        <CardHeader className="border-b border-border px-4 py-3">
          <CardTitle className="text-sm">Talk time</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
            {speakers.map(([name, secs], i) => (
              <div
                key={name}
                style={{
                  width: `${(secs / totalTalk) * 100}%`,
                  backgroundColor: TALK_COLORS[i % TALK_COLORS.length],
                }}
                title={`${name}: ${mmss(secs)}`}
              />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-4">
            {speakers.map(([name, secs], i) => (
              <div key={name} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm"
                  style={{ backgroundColor: TALK_COLORS[i % TALK_COLORS.length] }}
                />
                <span className="font-medium">{name}</span>
                <span className="tabular-nums text-muted-foreground">
                  {mmss(secs)} ({Math.round((secs / totalTalk) * 100)}%)
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border px-4 py-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            Flagged phrases
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          {data.flagged_phrases.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No compliance keywords detected in this call.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.flagged_phrases.map((f) => (
                <Badge key={f.phrase} variant="outline" className="gap-1.5">
                  {f.phrase}
                  <span className="tabular-nums text-muted-foreground">×{f.count}</span>
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
