"use client";

import { AlertTriangle, Inbox } from "lucide-react";
import type { Category, FindingRow } from "@/lib/types";
import { IMPACT_WORDS, rupees } from "@/lib/format";

const TONES = {
  ok: "bg-ok",
  bad: "bg-bad",
  dup: "bg-dup",
  miss: "bg-miss",
  orange: "bg-orange-deep",
  plain: "bg-ink-3",
} as const;
export type Tone = keyof typeof TONES;

export const CATEGORY_TONE: Record<Category, Tone> = { tax: "bad", missing: "miss", duplicate: "dup", matching: "orange", anomaly: "plain", filing: "bad" };
export const CATEGORY_NAME: Record<Category, string> = { tax: "Tax", missing: "Missing", duplicate: "Duplicate", matching: "Matching", anomaly: "Anomaly", filing: "Filing" };

export function Pill({ tone = "plain", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] font-semibold">
      <span className={`size-2 shrink-0 rounded-full ${TONES[tone]}`} aria-hidden />
      {children}
    </span>
  );
}

export function impactTone(type: FindingRow["impact_type"]): Tone {
  return type === "itc_found" ? "ok" : type === "itc_at_risk" ? "orange" : type === "none" ? "plain" : "bad";
}

export function ImpactPill({ finding }: { finding: Pick<FindingRow, "impact_type" | "impact_paise"> }) {
  if (finding.impact_type === "none") return <Pill>No rupee impact</Pill>;
  return (
    <Pill tone={impactTone(finding.impact_type)}>
      {rupees(finding.impact_paise)} {IMPACT_WORDS[finding.impact_type]}
    </Pill>
  );
}

export function StatusPill({ status }: { status: FindingRow["status"] }) {
  if (status === "approved") return <Pill tone="ok">Approved</Pill>;
  if (status === "dismissed") return <Pill>Dismissed</Pill>;
  return <Pill tone="orange">Open</Pill>;
}

export function BandBadge({ band, layer }: { band: string; layer?: string }) {
  if (layer === "one_to_many") return <Pill tone="miss">One-to-many</Pill>;
  if (band === "auto") return <Pill tone="ok">Auto-matched</Pill>;
  if (band === "review") return <Pill tone="dup">Review</Pill>;
  return <Pill>Unmatched</Pill>;
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center text-ink-2">
      <Inbox className="size-7 text-ink-3" aria-hidden />
      <p className="font-semibold text-ink">{title}</p>
      {hint && <p className="max-w-md text-[13px]">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-bad/30 bg-bad-soft p-4 text-ink">
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-bad" aria-hidden />
      <div className="flex-1">
        <p className="font-semibold">Something went wrong</p>
        <p className="text-[13px] text-ink-2">{message}</p>
      </div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}

export function PageTitle({ title, lead, right }: { title: string; lead: string; right?: React.ReactNode }) {
  return (
    <div className="mb-8 flex items-end justify-between gap-6 px-2">
      <div>
        <h1 className="font-display text-[48px] font-extrabold leading-none tracking-[-0.02em]">{title}</h1>
        <p className="mt-3 max-w-3xl text-[16px] leading-relaxed text-ink-2">{lead}</p>
      </div>
      {right}
    </div>
  );
}
