"use client";

import { useRouter } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CallForm } from "@/components/calls/call-form";

export default function NewCallPage() {
  const router = useRouter();

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New Call</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Upload a telephony recording and its metadata. The recording is written to B2;
          analysis runs the local SpeechBrain pipeline and writes a transcript and
          analytics alongside it.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2 max-w-3xl">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Call details</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <CallForm
              mode="create"
              onSuccess={(callId) => router.push(`/calls/${callId}`)}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
