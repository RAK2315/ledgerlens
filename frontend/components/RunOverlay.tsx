"use client";

import { useRun } from "@/lib/run-store";
import { periodName } from "@/lib/format";
import { ErrorState } from "./ui";
import { StageStepper } from "./StageStepper";

/** Covers the page while a Run is in progress, and stays up with a retry if it fails. */
export function RunOverlay({ onRetry }: { onRetry?: () => void }) {
  const run = useRun();
  const busy = run.runState === "loading" || run.runState === "running";
  if (!busy && run.runState !== "failed") return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-6 text-ink" role="dialog" aria-modal="true" aria-label="Run in progress">
      <div className="card w-full max-w-lg p-5 shadow-float">
        <p className="font-display text-xl font-bold">Reconciling {periodName(run.target)}</p>
        <p className="mb-3 text-[13px] text-ink-2">Each stage reports what it found.</p>
        <StageStepper events={run.stages} waiting={busy} />
        {run.runState === "failed" && (
          <div className="mt-3">
            <ErrorState message={run.runError ?? "The Run failed."} onRetry={onRetry ?? (() => run.launch())} />
          </div>
        )}
      </div>
    </div>
  );
}
