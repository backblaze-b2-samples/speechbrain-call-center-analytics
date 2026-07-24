"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCallStats } from "@/lib/queries";

const chartConfig = {
  calls: {
    label: "Calls",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

export function UploadChart() {
  const { data: stats, isLoading, error, refetch } = useCallStats();

  const data = useMemo(
    () =>
      Object.entries(stats?.queue_breakdown ?? {}).map(([queue, calls]) => ({
        queue: queue.charAt(0).toUpperCase() + queue.slice(1),
        calls,
      })),
    [stats],
  );

  const total = data.reduce((sum, d) => sum + d.calls, 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Calls by Queue</CardTitle>
        <CardDescription className="text-xs">Distribution across contact-center queues</CardDescription>
        <CardAction className="text-right self-center">
          {isLoading ? (
            <div aria-hidden className="space-y-1">
              <Skeleton className="ml-auto h-2.5 w-10 motion-reduce:animate-none" />
              <Skeleton className="ml-auto h-6 w-12 motion-reduce:animate-none" />
            </div>
          ) : (
            <>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Total
              </div>
              <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
                {stats ? total : "-"}
              </div>
            </>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No calls yet"
            description="Ingest calls to see the queue breakdown here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="calls-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-calls)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-calls)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="queue" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={28} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar dataKey="calls" fill="url(#calls-fill)" radius={[4, 4, 0, 0]} animationDuration={500} animationEasing="ease-out" />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
