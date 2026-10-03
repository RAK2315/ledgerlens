"use client";

// Direction B, "front page": one dark headline band, large type, the next action beside the number.
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { IMPACT_WORDS, percent, periodName, rupees, rupeesShort } from "@/lib/format";
import type { Category, FindingRow } from "@/lib/types";
import { FindingDrawer } from "@/components/FindingDrawer";
import { CATEGORY_NAME, Skeleton } from "@/components/ui";

export default function DashboardB() {
  const { summary, runId } = useRun();
  const [openId, setOpenId] = useState<string | null>(null);
  const [rateChange, setRateChange] = useState<FindingRow[]>([]);
  const [showCounts, setShowCounts] = useState(false);

  useEffect(() => {
    if (!runId) return;
    api
      .findings(runId, { finding_type: "WRONG_TAX_RATE", status: "open" })
      .then((r) => setRateChange(r.items.filter((f) => f.title.includes(" since "))))
      .catch(() => setRateChange([]));
  }, [runId, summary]);

  if (!summary)
    return (
      <div className="grid gap-6">
        <Skeleton className="h-72" />
        <Skeleton className="h-80" />
      </div>
    );

  const c = summary.match_counts;
  const settled = c.auto + c.one_to_many;
  const allMatches = settled + c.review + c.unmatched || 1;
  const openFindings = summary.finding_counts_by_status.open ?? 0;
  const largest = Math.max(1, ...summary.itc_at_risk_by_cause.map((x) => x.paise));
  const first = summary.top_findings[0];
  const bands = [
    { label: "Matched automatically", value: c.auto, colour: "var(--ok)" },
    { label: "One-to-many", value: c.one_to_many, colour: "var(--miss)" },
    { label: "Needs review", value: c.review, colour: "var(--dup)" },
    { label: "Unmatched", value: c.unmatched, colour: "var(--bad)" },
  ];

  return (
    <div className="grid gap-10">
      <section className="grid grid-cols-[minmax(0,1fr)_380px] gap-10 rounded-[20px] bg-side px-10 py-9 text-cream">
        <div>
          <p className="text-[15px] text-cream/70">
            {periodName(summary.period)} · {summary.invoice_count.toLocaleString("en-IN")} invoices · {openFindings} open Findings
          </p>
          <h1 className="mt-3 max-w-[18ch] font-display text-[54px] font-extrabold leading-[1.02] tracking-[-0.02em]">
            <span className="text-orange">{rupeesShort(summary.itc_at_risk_paise)}</span> of tax credit is at risk this month.
          </h1>
          <dl className="mt-8 flex gap-12">
            <div>
              <dt className="text-[15px] text-cream/70">ITC found, not yet claimed</dt>
              <dd className="font-display text-[34px] font-bold leading-tight text-ok-soft">{rupeesShort(summary.itc_found_paise)}</dd>
            </div>
            <div>
              <dt className="text-[15px] text-cream/70">Net payable</dt>
              <dd className="font-display text-[34px] font-bold leading-tight">{rupeesShort(summary.net_payable_paise)}</dd>
            </div>
            <div>
              <dt className="text-[15px] text-cream/70">Tax charged in excess / short</dt>
              <dd className="font-display text-[34px] font-bold leading-tight">
                {rupeesShort(summary.excess_tax_paise)} <span className="text-cream/40">/</span> {rupeesShort(summary.short_tax_paise)}
              </dd>
            </div>
          </dl>
        </div>

        {first && (
          <div className="flex flex-col justify-between border-l border-white/15 pl-10">
            <div>
              <p className="text-[15px] font-semibold text-orange">Start here</p>
              <p className="mt-2 font-display text-[24px] font-bold leading-snug">{first.title}</p>
              <p className="mt-2 text-[15px] text-cream/70">The evidence, the rule and a drafted fix are ready to review.</p>
            </div>
            <button onClick={() => setOpenId(first.id)} className="btn btn-primary mt-6 self-start px-5 py-3 text-[15px]">
              See why and fix <ArrowRight className="size-4" aria-hidden />
            </button>
          </div>
        )}
      </section>

      {rateChange.length > 0 && (
        <button onClick={() => setOpenId(rateChange[0].id)} className="group -my-4 flex w-full items-center gap-4 px-2 text-left text-[16px]">
          <span className="size-2.5 shrink-0 rounded-full bg-bad" aria-hidden />
          <span className="flex-1">
            <b>GST rates changed on 22 Sep 2025.</b> {rateChange.length} {rateChange.length === 1 ? "invoice" : "invoices"} this month still {rateChange.length === 1 ? "uses" : "use"} the old rate,{" "}
            {rupees(rateChange.reduce((sum, f) => sum + f.impact_paise, 0))} in all.
          </span>
          <span className="inline-flex items-center gap-1 font-semibold text-orange-deep group-hover:underline">
            See why and fix <ArrowRight className="size-4" aria-hidden />
          </span>
        </button>
      )}

      <div className="grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] gap-12 px-2">
        <section>
          <h2 className="font-display text-[28px] font-bold leading-tight">Fix these first</h2>
          <ol className="mt-4">
            {summary.top_findings.map((f, i) => (
              <li key={f.id} className="border-t border-line first:border-t-2 first:border-ink">
                <button onClick={() => setOpenId(f.id)} className="group grid w-full grid-cols-[28px_150px_1fr_auto] items-center gap-4 py-4 text-left">
                  <span className="font-display text-[20px] font-bold text-ink-3">{i + 1}</span>
                  <span className="font-display text-[26px] font-bold leading-none">{f.impact_type === "none" ? "" : rupees(f.impact_paise)}</span>
                  <span>
                    <span className="text-[16px] font-semibold">{f.label}</span>
                    <span className="block text-[14px] text-ink-2">
                      {f.party?.name ?? "Company"}, <span className="font-mono text-[13px]">{f.record_refs[0]?.id}</span>, {IMPACT_WORDS[f.impact_type]}
                    </span>
                  </span>
                  <ArrowRight className="size-5 text-orange-deep transition-transform group-hover:translate-x-1" aria-hidden />
                </button>
              </li>
            ))}
          </ol>
          <Link href="/workbench" className="mt-4 inline-flex items-center gap-1 text-[16px] font-semibold text-orange-deep hover:underline">
            All {openFindings} Findings <ArrowRight className="size-4" aria-hidden />
          </Link>
        </section>

        <section>
          <h2 className="font-display text-[28px] font-bold leading-tight">Why credit is at risk</h2>
          <ol className="mt-4 grid gap-4 border-t-2 border-ink pt-5">
            {summary.itc_at_risk_by_cause.slice(0, 6).map((cause) => (
              <li key={cause.finding_type}>
                <div className="flex items-baseline justify-between gap-4 text-[15px]">
                  <span>{cause.label}</span>
                  <span className="font-mono font-semibold">{rupees(cause.paise)}</span>
                </div>
                <div className="mt-1.5 h-2.5 rounded-full bg-line-2">
                  <div className="h-full rounded-full bg-orange" style={{ width: `${Math.max(1.5, (cause.paise / largest) * 100)}%` }} />
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <section className="px-2">
        <button onClick={() => setShowCounts((v) => !v)} aria-expanded={showCounts} className="flex w-full items-baseline justify-between border-t border-line pt-5 text-left">
          <span className="font-display text-[28px] font-bold leading-tight">
            {percent(settled / allMatches, 1)} of matches needed no one
          </span>
          <span className="text-[15px] font-semibold text-orange-deep">{showCounts ? "Hide the counts" : "Show the counts"}</span>
        </button>
        {showCounts && (
          <div className="mt-5">
            <div className="flex h-4 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={bands.map((b) => `${b.label}: ${b.value}`).join(", ")}>
              {bands.map((b) => b.value > 0 && <span key={b.label} style={{ flexGrow: b.value, background: b.colour, minWidth: 4 }} />)}
            </div>
            <dl className="mt-5 flex flex-wrap gap-x-12 gap-y-4">
              {bands.map((b) => (
                <div key={b.label}>
                  <dd className="font-display text-[30px] font-bold leading-none">{b.value.toLocaleString("en-IN")}</dd>
                  <dt className="mt-1 flex items-center gap-2 text-[14px] text-ink-2">
                    <span className="size-2.5 rounded-full" style={{ background: b.colour }} aria-hidden /> {b.label}
                  </dt>
                </div>
              ))}
              {(Object.entries(summary.finding_counts_by_category) as [Category, number][]).map(([category, count]) => (
                <div key={category}>
                  <dd className="font-display text-[30px] font-bold leading-none">{count}</dd>
                  <dt className="mt-1 text-[14px] text-ink-2">{CATEGORY_NAME[category]} Findings</dt>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>

      <FindingDrawer findingId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
