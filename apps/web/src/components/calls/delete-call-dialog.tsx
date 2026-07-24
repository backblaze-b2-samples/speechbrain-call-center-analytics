"use client";

import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { useDeleteCall } from "@/lib/queries";

export function DeleteCallDialog({
  callId,
  title,
  open,
  onOpenChange,
  onDeleted,
}: {
  callId: string;
  title: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}) {
  const deleteMutation = useDeleteCall();

  const confirm = () => {
    deleteMutation.mutate(callId, {
      onSuccess: (res) => {
        toast.success(`Deleted "${title}"`, {
          description: `${res.objects} object(s) removed from B2.`,
        });
        onDeleted();
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? err.message : "Failed to delete call");
      },
      onSettled: () => onOpenChange(false),
    });
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle>Delete call?</AlertDialogTitle>
          <AlertDialogDescription className="break-words">
            This permanently deletes{" "}
            <strong className="font-semibold text-foreground">{title}</strong> — the
            recording and every derived artifact (transcript, analytics) under its B2
            prefix. This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={deleteMutation.isPending}
            className={buttonVariants({ variant: "destructive" })}
          >
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
