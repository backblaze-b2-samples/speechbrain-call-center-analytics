"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Inbox } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { StatusBadge, SentimentBadge } from "@/components/calls/call-badges";

export function RecentUploadsTable() {
  const { data: calls = [], isLoading, error, refetch } = useCalls();
  const router = useRouter();
  const recent = calls.slice(0, 8);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Calls</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/calls"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No calls yet"
            description="Head to Calls to ingest your first recording."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[40%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Title
                </TableHead>
                <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Queue
                </TableHead>
                <TableHead className="w-[20%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Sentiment
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((call) => (
                <TableRow
                  key={call.call_id}
                  className="cursor-pointer table-row-hover"
                  onClick={() => router.push(`/calls/${call.call_id}`)}
                >
                  <TableCell className="font-medium">
                    <div className="truncate">{call.title}</div>
                  </TableCell>
                  <TableCell className="capitalize text-muted-foreground whitespace-nowrap">
                    {call.queue}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <SentimentBadge label={call.sentiment_label} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
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
