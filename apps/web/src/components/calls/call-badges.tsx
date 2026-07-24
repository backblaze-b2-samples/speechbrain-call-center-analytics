import { Badge } from "@/components/ui/badge";
import type { CallStatus } from "@speechbrain-call-center-analytics/shared";

const STATUS_STYLES: Record<CallStatus, string> = {
  uploaded: "bg-muted text-muted-foreground",
  processing: "bg-[var(--chart-1)]/15 text-[var(--chart-1)]",
  done: "bg-[var(--success)]/15 text-[var(--success)]",
  error: "bg-destructive/15 text-destructive",
};

const STATUS_LABEL: Record<CallStatus, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  done: "Done",
  error: "Error",
};

export function StatusBadge({ status }: { status: CallStatus }) {
  return (
    <Badge variant="outline" className={`border-0 font-medium ${STATUS_STYLES[status]}`}>
      {status === "processing" && (
        <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {STATUS_LABEL[status]}
    </Badge>
  );
}

function sentimentStyle(label: string | null | undefined): string {
  if (label === "positive") return "bg-[var(--success)]/15 text-[var(--success)]";
  if (label === "negative") return "bg-destructive/15 text-destructive";
  return "bg-muted text-muted-foreground";
}

export function SentimentBadge({ label }: { label: string | null | undefined }) {
  if (!label) return <span className="text-muted-foreground">—</span>;
  return (
    <Badge variant="outline" className={`border-0 capitalize font-medium ${sentimentStyle(label)}`}>
      {label}
    </Badge>
  );
}
