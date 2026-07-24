"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PhoneCall, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useCalls } from "@/lib/queries";
import { StatusBadge, SentimentBadge } from "./call-badges";

const QUEUES = ["sales", "support", "billing", "retention", "collections"] as const;
const ALL = "all";

export function CallLibraryTable() {
  const router = useRouter();
  const [queue, setQueue] = useState<string>(ALL);
  const [date, setDate] = useState<string>("");

  const { data: calls = [], isLoading, isFetching, error, refetch } = useCalls(
    queue === ALL ? undefined : queue,
    date || undefined,
  );

  const rows = useMemo(() => calls, [calls]);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle className="card-title">Call Library</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={queue} onValueChange={setQueue}>
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue placeholder="All queues" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All queues</SelectItem>
              {QUEUES.map((q) => (
                <SelectItem key={q} value={q} className="capitalize">
                  {q}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-8 w-40 text-xs"
            aria-label="Filter by date"
          />
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} title="Couldn't load calls" onRetry={() => refetch()} className="px-4" />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={PhoneCall}
            title="No calls yet"
            description="Ingest a recording to start transcribing and analyzing calls."
            action={
              <Button asChild size="sm">
                <Link href="/calls/new">New call</Link>
              </Button>
            }
            className="px-4"
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Title</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Queue</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Date</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Speakers</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sentiment</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((call) => (
                <TableRow
                  key={call.call_id}
                  className="cursor-pointer table-row-hover"
                  onClick={() => router.push(`/calls/${call.call_id}`)}
                >
                  <TableCell className="font-medium">
                    <div className="truncate max-w-[280px]">{call.title}</div>
                  </TableCell>
                  <TableCell className="capitalize text-muted-foreground">{call.queue}</TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">{call.date}</TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {call.num_speakers ?? "—"}
                  </TableCell>
                  <TableCell>
                    <SentimentBadge label={call.sentiment_label} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={call.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
