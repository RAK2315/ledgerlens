"use client";

import { Check, Loader2 } from "lucide-react";
import type { StageEvent } from "@/lib/types";

export const STAGES: { id: string; label: string; what: string }[] = [
  { id: "read", label: "Reading records", what: "Invoices, ledger, bank statement and GSTR-2B" },
  { id: "clean", label: "Cleaning up", what: "Invoice numbers and names written in different ways" },
  { id: "match", label: "Matching", what: "Each invoice to its booking, its payment and the Supplier's filing" },
  { id: "check", label: "Checking tax", what: "Rate on the invoice date, tax type, arithmetic, duplicates, 180-day rule" },
  { id: "anomalies", label: "Looking for anomalies", what: "Unusual invoices and Suppliers linked to Customers" },
  { id: "money", label: "Working out the money", what: "ITC at risk, ITC found and Net payable" },
  { id: "explain", label: "Writing explanations", what: "A reason and a next step for every Finding" },
];

export function StageStepper({ events, waiting }: { events: StageEvent[]; waiting?: boolean }) {
  const state = new Map<string, StageEvent>();
  for (const event of events) state.set(event.stage, event);
  return (
    <ol className="flex flex-col gap-1" aria-live="polite">
      {STAGES.map((stage, index) => {
        const event = state.get(stage.id);
        const done = event?.status === "done";
        const active = event?.status === "started" || (waiting && index === 0 && !event);
        return (
          <li key={stage.id} className={`flex items-start gap-3 rounded-lg px-3 py-2 ${active ? "bg-orange-soft/50" : ""}`}>
            <span
              className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold ${
                done ? "bg-ok text-white" : active ? "bg-orange-deep text-white" : "bg-line-2 text-ink-3"
              }`}
            >
              {done ? <Check className="size-3.5" aria-hidden /> : active ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : index + 1}
            </span>
            <div className="min-w-0">
              <p className={`font-semibold ${done || active ? "text-ink" : "text-ink-3"}`}>{stage.label}</p>
              <p className="text-[13px] text-ink-2">{done ? event.message : stage.what}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
