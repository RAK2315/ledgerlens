"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { periodName } from "@/lib/format";
import type { FeedItem, StageEvent } from "@/lib/types";
import { ErrorState } from "./ui";
import { RunFeed } from "./RunFeed";

const NOTE = "The lines are real records and results from this month. Code decides every number; the language model only words explanations and drafts.";

function Frame({ title, children, onClose }: { title: string; children: React.ReactNode; onClose?: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-6 text-ink" role="dialog" aria-modal="true" aria-label={title}>
      <div className="panel w-full max-w-[880px] px-8 py-7 shadow-float">
        <div className="mb-4 flex items-start justify-between gap-6">
          <div>
            <p className="font-display text-[34px] font-extrabold leading-none tracking-[-0.02em]">{title}</p>
            <p className="mt-2 max-w-[70ch] text-[14px] text-ink-2">{NOTE}</p>
          </div>
          {onClose && (
            <button className="btn px-2 py-1.5" onClick={onClose} aria-label="Close">
              <X className="size-4" aria-hidden />
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}

/** Covers the page while a Run is in progress, and stays up with a retry if it fails. */
export function RunOverlay({ onRetry }: { onRetry?: () => void }) {
  const run = useRun();
  const busy = run.runState === "loading" || run.runState === "running";
  if (!busy && run.runState !== "failed") return null;
  return (
    <Frame title={`Reconciling ${periodName(run.target)}`}>
      <RunFeed stages={run.stages} items={run.items} waiting={busy} />
      {run.runState === "failed" && (
        <div className="mt-3">
          <ErrorState message={run.runError ?? "The Run failed."} onRetry={onRetry ?? (() => run.launch())} />
        </div>
      )}
    </Frame>
  );
}

/** The same feed for a finished Run, read back from the server so it can be opened at any time. */
export function RunLog({ runId, period, onClose }: { runId: string; period: string; onClose: () => void }) {
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [items, setItems] = useState<FeedItem[]>([]);

  useEffect(() => {
    const events = new EventSource(api.eventsUrl(runId));
    events.addEventListener("stage", (e) => setStages((all) => [...all, JSON.parse((e as MessageEvent).data)]));
    events.addEventListener("item", (e) => setItems((all) => [...all, JSON.parse((e as MessageEvent).data)]));
    events.addEventListener("done", () => events.close());
    events.onerror = () => events.close();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => {
      events.close();
      document.removeEventListener("keydown", onKey);
    };
  }, [runId, onClose]);

  return (
    <Frame title={`How ${periodName(period)} was reconciled`} onClose={onClose}>
      <RunFeed stages={stages} items={items} waiting={false} />
    </Frame>
  );
}
