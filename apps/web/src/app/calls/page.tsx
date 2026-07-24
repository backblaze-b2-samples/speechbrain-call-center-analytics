import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CallLibraryTable } from "@/components/calls/call-library-table";

export default function CallsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Calls</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Ingest, transcribe, diarize and analyze call recordings — every artifact
            stored on Backblaze B2 under a <code className="text-xs">date/queue</code> prefix.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/calls/new">
            <Plus aria-hidden="true" className="h-3.5 w-3.5" />
            New call
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CallLibraryTable />
      </div>
    </div>
  );
}
