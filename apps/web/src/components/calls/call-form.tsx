"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateCall, useUpdateCall } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { Call } from "@speechbrain-call-center-analytics/shared";

const QUEUES = ["sales", "support", "billing", "retention", "collections"] as const;

const schema = z.object({
  title: z.string().min(1, "Title is required").max(200),
  queue: z.enum(QUEUES),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Use YYYY-MM-DD"),
  expected_speakers: z.enum(["2", "3", "auto"]),
  agent_label: z.string().min(1, "Required").max(60),
  customer_label: z.string().min(1, "Required").max(60),
  compliance_keywords: z.string().max(500),
  notes: z.string().max(1000),
});

type Values = z.infer<typeof schema>;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CallForm({
  mode,
  call,
  onSuccess,
}: {
  mode: "create" | "edit";
  call?: Call;
  onSuccess?: (callId: string) => void;
}) {
  const isCreate = mode === "create";
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [analyze, setAnalyze] = useState(true);

  const createMutation = useCreateCall();
  const updateMutation = useUpdateCall();

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: call?.title ?? "",
      queue: call?.queue ?? "support",
      date: call?.date ?? today(),
      expected_speakers: call?.expected_speakers ?? "2",
      agent_label: call?.agent_label ?? "Agent",
      customer_label: call?.customer_label ?? "Customer",
      compliance_keywords: (call?.compliance_keywords ?? []).join(", "),
      notes: call?.notes ?? "",
    },
  });

  const onSubmit = async (values: Values) => {
    if (isCreate && !file) {
      setFileError("A recording is required");
      return;
    }
    try {
      if (isCreate && file) {
        const created = await createMutation.mutateAsync({
          input: {
            file,
            title: values.title,
            queue: values.queue,
            date: values.date,
            expected_speakers: values.expected_speakers,
            agent_label: values.agent_label,
            customer_label: values.customer_label,
            compliance_keywords: values.compliance_keywords,
            notes: values.notes,
            analyze,
          },
        });
        toast.success("Call created", { description: values.title });
        onSuccess?.(created.call_id);
      } else if (call) {
        await updateMutation.mutateAsync({
          callId: call.call_id,
          patch: {
            title: values.title,
            expected_speakers: values.expected_speakers,
            agent_label: values.agent_label,
            customer_label: values.customer_label,
            compliance_keywords: values.compliance_keywords
              .split(",")
              .map((k) => k.trim())
              .filter(Boolean),
            notes: values.notes,
          },
        });
        toast.success("Call updated");
        onSuccess?.(call.call_id);
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Something went wrong";
      toast.error(detail);
    }
  };

  const submitting = createMutation.isPending || updateMutation.isPending;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {isCreate && (
          <div className="space-y-2">
            <FormLabel htmlFor="recording">Recording</FormLabel>
            <Input
              id="recording"
              type="file"
              accept="audio/wav,audio/x-wav,audio/mpeg,.wav,.mp3"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setFileError(null);
              }}
            />
            <p className="text-[0.8rem] text-muted-foreground">
              Telephony audio (WAV or MP3). Stored to B2 under its date/queue prefix.
            </p>
            {fileError && <p className="text-[0.8rem] text-destructive">{fileError}</p>}
          </div>
        )}

        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Title</FormLabel>
              <FormControl>
                <Input placeholder="e.g. Refund request — 2026-07-23" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-6 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="queue"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Queue</FormLabel>
                {isCreate ? (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {QUEUES.map((q) => (
                        <SelectItem key={q} value={q} className="capitalize">
                          {q}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input value={field.value} readOnly className="capitalize bg-muted/40" />
                )}
                {isCreate ? (
                  <FormDescription>Defaults to support — pick the queue this call came through.</FormDescription>
                ) : (
                  <FormDescription>Immutable — encoded in the object key.</FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Date</FormLabel>
                <FormControl>
                  <Input
                    type="date"
                    {...field}
                    readOnly={!isCreate}
                    className={!isCreate ? "bg-muted/40" : undefined}
                  />
                </FormControl>
                {!isCreate && (
                  <FormDescription>Immutable — encoded in the object key.</FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="expected_speakers"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Expected speakers</FormLabel>
              <FormControl>
                <RadioGroup
                  onValueChange={field.onChange}
                  value={field.value}
                  className="flex flex-wrap gap-6"
                >
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <RadioGroupItem value="2" /> 2 — agent + customer
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <RadioGroupItem value="3" /> 3
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <RadioGroupItem value="auto" /> Auto-detect
                  </label>
                </RadioGroup>
              </FormControl>
              {isCreate && (
                <FormDescription>
                  Most calls are 2 — agent + customer (the default). Seeds speaker clustering.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-6 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="agent_label"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Agent label</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="customer_label"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Customer label</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="compliance_keywords"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Compliance keywords</FormLabel>
              <FormControl>
                <Input placeholder="refund, complaint, supervisor" {...field} />
              </FormControl>
              <FormDescription>
                Comma-separated phrases flagged in the transcript. Leave blank to use the
                account defaults.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea className="resize-none" placeholder="Optional context for reviewers" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {isCreate && (
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={analyze} onCheckedChange={(v) => setAnalyze(!!v)} />
            Run analysis immediately after upload
          </label>
        )}

        <div className="flex justify-end gap-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : isCreate ? "Create call" : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
