"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CalendarClock, IndianRupee } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { periodName, rupees, rupeesShort } from "@/lib/format";
import type { FindingRow, Summary } from "@/lib/types";
import { FindingDrawer } from "@/components/FindingDrawer";
import { FindingTable } from "@/components/FindingTable";
import { EmptyState, Skeleton } from "@/components/ui";

const CAUSE_COLOURS = ["var(--miss)", "var(--bad)", "var(--orange)", "var(--dup)", "var(--ink-3)"];

function MoneyTile({ tone, label, value, note }: { tone: "risk" | "found" | "plain"; label: string; value: string; note: string }) {
  const styles = { risk: "border-orange/50 bg-orange-soft/60 text-orange-deep", found: "border-ok/40 bg-ok-soft text-ok", plain: "border-line bg-paper text-ink" }[tone];
  return (
    <div className={`rounded-xl border p-4 ${styles}`}>
      <p className="flex items-center gap-1.5 font-semibold">
        <IndianRupee className="size-4" aria-hidden /> {label}
      </p>
      <p className="font-display text-[38px] font-extrabold leading-tight">{value}</p>
      <p className="text-[13px] text-ink-2">{note}</p>
    </div>
  );
}

function CountTile({ dot, label, value, note }: { dot: string; label: string; value: string; note: string }) {
  return (
    <div className="card p-4">
      <p className="flex items-center gap-2 font-semibold text-ink-2">
        <span className="size-2.5 rounded-full" style={{ background: dot }} aria-hidden /> {label}
      </p>
      <p className="font-display text-[30px] font-extrabold leading-tight">{value}</p>
      <p className="text-[13px] text-ink-3">{note}</p>
    </div>
  );
}

function Donut({ summary }: { summary: Summary }) {
  const c = summary.match_counts;
  const parts = [
    { label: "Matched automatically", value: c.auto, colour: "var(--ok)" },
    { label: "One-to-many", value: c.one_to_many, colour: "var(--miss)" },
    { label: "Needs review", value: c.review, colour: "var(--dup)" },
    { label: "Unmatched", value: c.unmatched, colour: "var(--bad)" },
  ];
  const total = parts.reduce((sum, p) => sum + p.value, 0) || 1;
  const matched = Math.round(((c.auto + c.one_to_many) / total) * 100);
  const radius = 54;
  const around = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 140 140" className="size-40 shrink-0 -rotate-90" role="img" aria-label={`${matched} percent of matches are settled`}>
        {parts.map((p) => {
          const length = (p.value / total) * around;
          const arc = <circle key={p.label} cx="70" cy="70" r={radius} fill="none" stroke={p.colour} strokeWidth="18" strokeDasharray={`${length} ${around - length}`} strokeDashoffset={-offset} />;
          offset += length;
          return arc;
        })}
        <text x="70" y="68" textAnchor="middle" transform="rotate(90 70 70)" className="fill-ink font-display text-[26px] font-extrabold">
          {matched}%
        </text>
        <text x="70" y="86" textAnchor="middle" transform="rotate(90 70 70)" className="fill-ink-3 text-[10px]">
          matched
        </text>
      </svg>
      <ul className="grid gap-1.5 text-[13px]">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center gap-2">
            <span className="size-2.5 rounded-full" style={{ background: p.colour }} aria-hidden />
            <span className="text-ink-2">{p.label}</span>
            <span className="ml-auto pl-4 font-mono font-semibold">{p.value.toLocaleString("en-IN")}</span>
          </li>
        ))}
        <li className="mt-1 border-t border-line-2 pt-1.5 text-[12px] text-ink-3">{c.open} invoices are open (not yet due or unpaid), which is normal.</li>
      </ul>
    </div>
  );
}

export default function DashboardPage() {
  const { summary, runId } = useRun();
  const [openId, setOpenId] = useState<string | null>(null);
  const [rateChange, setRateChange] = useState<FindingRow[] | null>(null);

  useEffect(() => {
    if (!runId) return;
    api
      .findings(runId, { finding_type: "WRONG_TAX_RATE", status: "open" })
      .then((r) => setRateChange(r.items.filter((f) => f.title.includes(" since "))))
      .catch(() => setRateChange([]));
  }, [runId, summary]);

  if (!summary)
    return (
      <div className="grid gap-4">
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-56" />
        <Skeleton className="h-64" />
      </div>
    );

  const counts = summary.finding_counts_by_category;
  const c = summary.match_counts;
  const settled = c.auto + c.one_to_many;
  const totalMatches = settled + c.review + c.unmatched || 1;
  const openFindings = Object.values(counts).reduce((a, b) => a + (b ?? 0), 0);
  const largest = Math.max(1, ...summary.itc_at_risk_by_cause.map((x) => x.paise));
  const rateTotal = (rateChange ?? []).reduce((sum, f) => sum + f.impact_paise, 0);

  return (
    <div className="grid gap-4">
      <p className="text-ink-2">
        <b className="text-ink">{periodName(summary.period)}:</b> {summary.invoice_count.toLocaleString("en-IN")} invoices checked against the ledger, the bank statement and
        GSTR-2B. {openFindings} Findings are open, each with its rupee effect, the reason and a drafted fix.
      </p>

      <div className="grid grid-cols-3 gap-4">
        <MoneyTile tone="risk" label="ITC at risk" value={rupeesShort(summary.itc_at_risk_paise)} note="Credit claimed that may be lost unless fixed" />
        <MoneyTile tone="found" label="ITC found" value={rupeesShort(summary.itc_found_paise)} note="In GSTR-2B, not yet claimed in your books" />
        <MoneyTile
          tone="plain"
          label="Net payable"
          value={rupeesShort(summary.net_payable_paise)}
          note={`Output tax minus eligible credit. ${rupees(summary.excess_tax_paise)} charged in excess, ${rupees(summary.short_tax_paise)} short.`}
        />
      </div>

      <div className="grid grid-cols-5 gap-4">
        <CountTile dot="var(--ok)" label="Matched" value={settled.toLocaleString("en-IN")} note={`${((settled / totalMatches) * 100).toFixed(1)}% of matches`} />
        <CountTile dot="var(--bad)" label="Discrepant" value={String((counts.tax ?? 0) + (counts.matching ?? 0) + (counts.filing ?? 0))} note="rate, amount, date, tax type" />
        <CountTile dot="var(--dup)" label="Duplicates" value={String(counts.duplicate ?? 0)} note="entered, booked or paid twice" />
        <CountTile dot="var(--miss)" label="Missing" value={String(counts.missing ?? 0)} note="not in GSTR-2B, books or bank" />
        <CountTile dot="var(--ink-3)" label="Anomalies" value={String(counts.anomaly ?? 0)} note="unusual, each with a reason" />
      </div>

      {rateChange && rateChange.length > 0 && (
        <button
          onClick={() => setOpenId(rateChange[0].id)}
          className="flex w-full items-center gap-3 rounded-xl border border-bad/30 bg-bad-soft px-4 py-3 text-left hover:brightness-[0.98]"
        >
          <CalendarClock className="size-5 shrink-0 text-bad" aria-hidden />
          <span className="flex-1">
            <b>GST rates changed on 22 Sep 2025.</b> {rateChange.length} {rateChange.length === 1 ? "invoice" : "invoices"} dated after the change still {rateChange.length === 1 ? "uses" : "use"} the old rate, {rupees(rateTotal)} in all. Largest:{" "}
            <span className="font-mono">{rateChange[0].record_refs[0]?.id}</span>.
          </span>
          <span className="flex items-center gap-1 font-semibold text-bad">
            See why and fix <ArrowRight className="size-4" aria-hidden />
          </span>
        </button>
      )}

      <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4">
        <section className="card p-5">
          <h2 className="mb-3 font-display text-lg font-bold">Match status</h2>
          <Donut summary={summary} />
        </section>
        <section className="card p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-display text-lg font-bold">ITC at risk by cause</h2>
            <span className="text-[13px] text-ink-3">sorted by rupees, each invoice counted once</span>
          </div>
          {summary.itc_at_risk_by_cause.length === 0 ? (
            <EmptyState title="No ITC at risk in this period" />
          ) : (
            <ul className="grid gap-2.5">
              {summary.itc_at_risk_by_cause.slice(0, 6).map((cause, i) => (
                <li key={cause.finding_type} className="grid grid-cols-[minmax(0,260px)_1fr_auto] items-center gap-3">
                  <span className="truncate">{cause.label}</span>
                  <span className="h-3.5 rounded-full bg-line-2">
                    <span className="block h-full rounded-full" style={{ width: `${Math.max(2, (cause.paise / largest) * 100)}%`, background: CAUSE_COLOURS[Math.min(i, CAUSE_COLOURS.length - 1)] }} />
                  </span>
                  <span className="w-24 text-right font-mono font-semibold">{rupeesShort(cause.paise)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card p-5">
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="font-display text-lg font-bold">Top Findings</h2>
          <span className="text-[13px] text-ink-3">
            {summary.top_findings.length} of {openFindings} · ranked by rupees ·{" "}
            <Link href="/workbench" className="font-semibold text-orange-deep">
              see all
            </Link>
          </span>
        </div>
        {summary.top_findings.length === 0 ? (
          <EmptyState title="No open Findings in this period" hint="Every Finding has been approved or dismissed." />
        ) : (
          <FindingTable rows={summary.top_findings} onOpen={setOpenId} />
        )}
      </section>

      <FindingDrawer findingId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
