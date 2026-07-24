"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Pencil, Play, Sparkles, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { useAnalyzeCall, useCall, useCallAudio } from "@/lib/queries";
import { StatusBadge } from "@/components/calls/call-badges";
import { CallForm } from "@/components/calls/call-form";
import { TranscriptViewer } from "@/components/calls/transcript-viewer";
import { AnalyticsPanel } from "@/components/calls/analytics-panel";
import { DeleteCallDialog } from "@/components/calls/delete-call-dialog";

export default function CallDetailPage() {
  const params = useParams<{ callId: string }>();
  const callId = params.callId;
  const router = useRouter();

  const { data: call, isLoading, error, refetch } = useCall(callId);
  const { data: audio } = useCallAudio(callId, !!call);
  const analyzeMutation = useAnalyzeCall();

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error || !call) {
    return (
      <div className="space-y-6">
        <Button asChild variant="ghost" size="sm">
          <Link href="/calls">
            <ArrowLeft className="h-4 w-4" /> Back to calls
          </Link>
        </Button>
        <ErrorState
          error={error ?? new ApiError("Call not found", 404)}
          title="Couldn't load this call"
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const done = call.status === "done";
  const processing = call.status === "processing";

  const runAnalysis = () => {
    analyzeMutation.mutate(callId, {
      onSuccess: () => toast.info("Analysis started — this can take a while on CPU."),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Failed to start analysis"),
    });
  };

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link href="/calls">
          <ArrowLeft className="h-4 w-4" /> Back to calls
        </Link>
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="page-title truncate">{call.title}</h1>
            <StatusBadge status={call.status} />
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            <span className="capitalize">{call.queue}</span> · {call.date}
            {call.duration_sec ? ` · ${Math.round(call.duration_sec)}s` : ""}
            {call.num_speakers ? ` · ${call.num_speakers} speakers` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={runAnalysis} disabled={processing || analyzeMutation.isPending}>
            <Sparkles className="h-3.5 w-3.5" />
            {processing ? "Analyzing..." : done ? "Re-analyze" : "Analyze"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="h-3.5 w-3.5" /> Edit
          </Button>
          <Button size="sm" variant="outline" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </Button>
        </div>
      </div>

      {call.status === "error" && (
        <Alert variant="destructive">
          <AlertTitle>Analysis failed</AlertTitle>
          <AlertDescription>{call.error || "Unknown error — try re-analyzing."}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="border-b border-border px-5 py-4">
          <CardTitle className="card-title flex items-center gap-2">
            <Play className="h-4 w-4 text-muted-foreground" /> Recording
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          {audio?.url ? (
            <audio controls preload="none" className="w-full" src={audio.url}>
              Your browser does not support the audio element.
            </audio>
          ) : (
            <Skeleton className="h-12 w-full" />
          )}
          <p className="mt-2 text-xs text-muted-foreground font-mono break-all">
            {call.recording_key}
          </p>
        </CardContent>
      </Card>

      <Tabs defaultValue="transcript">
        <TabsList>
          <TabsTrigger value="transcript">Transcript</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>
        <TabsContent value="transcript" className="mt-4">
          <TranscriptViewer callId={callId} enabled={done} />
        </TabsContent>
        <TabsContent value="analytics" className="mt-4">
          <AnalyticsPanel callId={callId} enabled={done} />
        </TabsContent>
      </Tabs>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit call</DialogTitle>
            <DialogDescription>
              Update metadata and analysis parameters. Queue and date are immutable.
              Re-analyze to apply changed parameters.
            </DialogDescription>
          </DialogHeader>
          <CallForm mode="edit" call={call} onSuccess={() => setEditOpen(false)} />
        </DialogContent>
      </Dialog>

      <DeleteCallDialog
        callId={callId}
        title={call.title}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => router.push("/calls")}
      />
    </div>
  );
}
