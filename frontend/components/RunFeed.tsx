"use client";

import { useEffect, useRef } from "react";
import { Check, Loader2 } from "lucide-react";
import type { FeedItem, StageEvent } from "@/lib/types";

const STAGES: { id: string; label: string; what: string }[] = [
  { id: "read", label: "Reading records", what: "Invoices, ledger, bank statement and GSTR-2B" },
  { id: "clean", label: "Cleaning up", what: "Invoice numbers and names written in different ways" },
  { id: "match", label: "Matching", what: "Each invoice to its booking, its payment and the Supplier's filing" },
  { id: "check", label: "Checking tax", what: "Rate on the invoice date, tax type, arithmetic, duplicates, 180-day rule" },
  { id: "anomalies", label: "Looking for anomalies", what: "Unusual invoices and Suppliers linked to Customers" },
  { id: "money", label: "Working out the money", what: "ITC at risk, ITC found and Net payable" },
  { id: "explain", label: "Writing explanations", what: "A reason and a next step for every Finding" },
];

/** The stages of a Run with the real records each one touched, newest stage at the bottom. */
export function RunFeed({ stages, items, waiting, inPage = false }: { stages: StageEvent[]; items: FeedItem[]; waiting: boolean; inPage?: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  const state = new Map<string, StageEvent>();
  for (const event of stages) state.set(event.stage, event);

  useEffect(() => {
    // Inside a page the feed grows in place; in the overlay it keeps the newest line in view.
    if (waiting && !inPage) end.current?.scrollIntoView({ block: "end" });
  }, [items.length, stages.length, waiting, inPage]);

  return (
    <ol className={inPage ? "" : "max-h-[62vh] overflow-y-auto pr-3"} aria-live={inPage ? "off" : "polite"}>
      {STAGES.map((stage, index) => {
        const event = state.get(stage.id);
        const done = event?.status === "done";
        const active = event?.status === "started" || (waiting && index === 0 && !event);
        const lines = items.filter((item) => item.stage === stage.id);
        if (!event && !active) {
          return (
            <li key={stage.id} className="flex items-baseline gap-4 border-t border-line py-2.5 text-ink-3">
              <span className="w-6 text-right font-display text-[18px] font-bold">{index + 1}</span>
              <span className="text-[16px] font-semibold">{stage.label}</span>
            </li>
          );
        }
        return (
          <li key={stage.id} className="border-t border-line py-3">
            <div className="flex items-baseline gap-4">
              <span className="flex w-6 justify-end self-center">
                {done ? <Check className="size-5 text-ok" aria-hidden /> : <Loader2 className="size-5 animate-spin text-orange-deep" aria-hidden />}
              </span>
              <span className="font-display text-[20px] font-bold leading-tight">{stage.label}</span>
              <span className="ml-auto text-right text-[14px] text-ink-2">{done ? event.message : stage.what}</span>
            </div>
            {lines.length > 0 && (
              <ul className="ml-10 mt-2 grid gap-1">
                {lines.map((item, i) => (
                  <li key={i} className="feed-line truncate font-mono text-[13px] text-ink-2">
                    {item.message}
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
      <div ref={end} />
    </ol>
  );
}
