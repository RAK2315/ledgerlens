"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useRun } from "@/lib/run-store";
import { RunOverlay } from "./RunOverlay";
import { ErrorState } from "./ui";

/** The landing page's main action: load the demo company, run September 2025, then open the dashboard. */
export function StartActions({ to = "/dashboard", onDark = false, withOverlay = false }: { to?: string; onDark?: boolean; withOverlay?: boolean }) {
  const run = useRun();
  const router = useRouter();
  const busy = run.runState === "loading" || run.runState === "running";

  async function start() {
    if (await run.launch()) router.push(to);
  }

  return (
    <div>
      {run.loadError && (
        <div className="mb-4 max-w-xl">
          <ErrorState message={run.loadError} onRetry={run.retry} />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <button className="btn btn-primary px-6 py-3.5 text-[16px]" onClick={start} disabled={!run.ready || !!run.loadError || busy}>
          {run.runId ? "Run again" : "Load demo company"}
        </button>
        {run.runId && (
          <Link href={to} className={`inline-flex items-center gap-1.5 text-[16px] font-semibold underline-offset-4 hover:underline ${onDark ? "text-cream" : "text-ink"}`}>
            Open dashboard <ArrowRight className="size-4" aria-hidden />
          </Link>
        )}
      </div>
      {withOverlay && <RunOverlay onRetry={start} />}
    </div>
  );
}
