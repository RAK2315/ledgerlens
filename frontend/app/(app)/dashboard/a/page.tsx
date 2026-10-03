"use client";

// Direction A, "working paper": no boxes, ruled lines, one column read top to bottom.
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { IMPACT_WORDS, percent, periodName, rupees, rupeesShort } from "@/lib/format";
import type { Category, FindingRow, Liability } from "@/lib/types";
import { FindingDrawer } from "@/components/FindingDrawer";
import { CATEGORY_NAME, Skeleton } from "@/components/ui";

function Part({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="grid grid-cols-12 gap-x-8 border-t border-line py-8">
      <div className="col-span-3">
        <h2 className="font-display text-[20px] font-bold leading-tight">{title}</h2>
        {note && <p className="mt-1.5 max-w-[26ch] text-[13px] text-ink-2">{note}</p>}
      </div>
      <div className="col-span-9">{children}</div>
    </section>
  );
}

function Figure({ label, value, note, colour }: { label: string; value: string; note: string; colour: string }) {
  return (
    <div className="px-8 first:pl-0 last:pr-0">
      <p className="text-[15px] font-semibold">{label}</p>
      <p className={`mt-1 font-display text-[56px] font-extrabold leading-none tracking-[-0.02em] ${colour}`}>{value}</p>
      <p className="mt-2 max-w-[34ch] text-[13px] text-ink-2">{note}</p>
    </div>
  );
}

export default function DashboardA() {
  const { summary, runId } = useRun();
  const [openId, setOpenId] = useState<string | null>(null);
  const [rateChange, setRateChange] = useState<FindingRow[]>([]);
  const [liability, setLiability] = useState<Liability | null>(null);

  useEffect(() => {
    if (!runId) return;
    api
      .findings(runId, { finding_type: "WRONG_TAX_RATE", status: "open" })
      .then((r) => setRateChange(r.items.filter((f) => f.title.includes(" since "))))
      .catch(() => setRateChange([]));
    api.liability(runId).then(setLiability).catch(() => setLiability(null));
  }, [runId, summary]);

  if (!summary)
    return (
      <div className="mx-auto grid max-w-[1180px] gap-6">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-36" />
        <Skeleton className="h-64" />
      </div>
    );

  const c = summary.match_counts;
  const settled = c.auto + c.one_to_many;
  const allMatches = settled + c.review + c.unmatched || 1;
  const openFindings = summary.finding_counts_by_status.open ?? 0;
  const atRisk = summary.itc_at_risk_paise || 1;
  const largest = Math.max(1, ...summary.itc_at_risk_by_cause.map((x) => x.paise));
  const output = liability?.by_tax_type.reduce((sum, t) => sum + t.output_paise, 0);
  const eligible = liability?.by_tax_type.reduce((sum, t) => sum + t.eligible_itc_paise, 0);
  const bands = [
    { label: "Matched automatically", value: c.auto, colour: "var(--ok)" },
    { label: "One payment or invoice against several", value: c.one_to_many, colour: "var(--miss)" },
    { label: "Needs a look", value: c.review, colour: "var(--dup)" },
    { label: "No match found", value: c.unmatched, colour: "var(--bad)" },
  ];

  return (
    <div className="mx-auto max-w-[1180px]">
      <h1 className="font-display text-[30px] font-bold leading-tight">{periodName(summary.period)}</h1>
      <p className="mt-1 text-[15px] text-ink-2">
        {summary.invoice_count.toLocaleString("en-IN")} invoices checked against the ledger, the bank statement and GSTR-2B. {openFindings} Findings are open.
      </p>

      <div className="mt-6 grid grid-cols-3 divide-x divide-line border-y-2 border-ink py-7">
        <Figure label="ITC at risk" value={rupeesShort(summary.itc_at_risk_paise)} colour="text-orange-deep" note="Credit already claimed that may be lost unless these Findings are fixed." />
        <Figure label="ITC found" value={rupeesShort(summary.itc_found_paise)} colour="text-ok" note="Credit showing in GSTR-2B that the books have not claimed yet." />
        <Figure
          label="Net payable"
          value={rupeesShort(summary.net_payable_paise)}
          colour="text-ink"
          note={output && eligible ? `Output tax ${rupeesShort(output)} less eligible credit ${rupeesShort(eligible)}.` : "Output tax less eligible credit."}
        />
      </div>

      {rateChange.length > 0 && (
        <button onClick={() => setOpenId(rateChange[0].id)} className="group flex w-full items-baseline gap-4 py-4 text-left text-[15px]">
          <span className="font-mono text-[13px] text-bad">22 Sep 2025</span>
          <span className="flex-1">
            GST rates changed. {rateChange.length} {rateChange.length === 1 ? "invoice" : "invoices"} this month still {rateChange.length === 1 ? "uses" : "use"} a rate that ended that day,{" "}
            {rupees(rateChange.reduce((sum, f) => sum + f.impact_paise, 0))} in all.
          </span>
          <span className="inline-flex items-center gap-1 font-semibold text-orange-deep group-hover:underline">
            See why and fix <ArrowRight className="size-4" aria-hidden />
          </span>
        </button>
      )}

      <Part title="Where the credit at risk comes from" note="Sorted by rupees. Each invoice is counted once.">
        {summary.itc_at_risk_by_cause.length === 0 ? (
          <p className="text-ink-2">No ITC at risk in this period.</p>
        ) : (
          <ol>
            {summary.itc_at_risk_by_cause.map((cause) => (
              <li key={cause.finding_type} className="grid grid-cols-[minmax(0,300px)_1fr_110px_48px] items-center gap-4 border-b border-line-2 py-2.5 text-[15px] last:border-b-0">
                <span className="truncate">{cause.label}</span>
                <span className="h-1.5 bg-line-2">
                  <span className="block h-full bg-orange-deep" style={{ width: `${Math.max(1, (cause.paise / largest) * 100)}%` }} />
                </span>
                <span className="text-right font-mono">{rupees(cause.paise)}</span>
                <span className="text-right font-mono text-[13px] text-ink-3">{percent(cause.paise / atRisk)}</span>
              </li>
            ))}
          </ol>
        )}
      </Part>

      <Part title="Fix these first" note={`The ${summary.top_findings.length} largest of ${openFindings} open Findings.`}>
        {summary.top_findings.length === 0 ? (
          <p className="text-ink-2">No open Findings in this period. Every Finding has been approved or dismissed.</p>
        ) : (
          <ul>
            {summary.top_findings.map((f) => (
              <li key={f.id} className="border-b border-line-2 last:border-b-0">
                <button onClick={() => setOpenId(f.id)} className="group grid w-full grid-cols-[120px_1fr_auto] items-baseline gap-4 py-3 text-left hover:bg-cream-2">
                  <span className="text-right font-mono text-[15px] font-semibold">{f.impact_type === "none" ? "" : rupees(f.impact_paise)}</span>
                  <span>
                    <span className="text-[15px] font-semibold">{f.label}</span>
                    <span className="mt-0.5 block text-[13px] text-ink-2">
                      {f.party?.name ?? "Company"} · <span className="font-mono">{f.record_refs[0]?.id}</span> · {IMPACT_WORDS[f.impact_type]} · {percent(f.confidence)} sure
                    </span>
                  </span>
                  <span className="inline-flex items-center gap-1 pr-2 text-[13px] font-semibold text-orange-deep group-hover:underline">
                    See why and fix <ArrowRight className="size-4" aria-hidden />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <Link href="/workbench" className="mt-4 inline-flex items-center gap-1 text-[15px] font-semibold text-orange-deep hover:underline">
          All {openFindings} Findings in the workbench <ArrowRight className="size-4" aria-hidden />
        </Link>
      </Part>

      <details className="group border-t border-line">
        <summary className="grid cursor-pointer list-none grid-cols-12 items-baseline gap-x-8 py-6 [&::-webkit-details-marker]:hidden">
          <span className="col-span-3 font-display text-[20px] font-bold leading-tight">How the month matched</span>
          <span className="col-span-8 text-[15px] text-ink-2">
            {settled.toLocaleString("en-IN")} of {allMatches.toLocaleString("en-IN")} matches settled without a person ({percent(settled / allMatches, 1)}).
          </span>
          <ChevronDown className="col-span-1 size-5 justify-self-end text-ink-3 transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="grid grid-cols-12 gap-x-8 pb-8">
          <div className="col-span-9 col-start-4">
            <div className="flex h-2.5 gap-px" role="img" aria-label={bands.map((b) => `${b.label}: ${b.value}`).join(", ")}>
              {bands.map((b) => b.value > 0 && <span key={b.label} style={{ flexGrow: b.value, background: b.colour, minWidth: 3 }} />)}
            </div>
            <dl className="mt-4 grid grid-cols-4 gap-6 text-[13px]">
              {bands.map((b) => (
                <div key={b.label}>
                  <dd className="font-mono text-[20px] font-semibold">{b.value.toLocaleString("en-IN")}</dd>
                  <dt className="mt-0.5 flex items-baseline gap-1.5 text-ink-2">
                    <span className="size-2 shrink-0 translate-y-[-1px]" style={{ background: b.colour }} aria-hidden /> {b.label}
                  </dt>
                </div>
              ))}
            </dl>
            <p className="mt-4 text-[13px] text-ink-2">{c.open} invoices are open (not yet due or unpaid), which is normal.</p>
            <p className="mt-5 text-[15px]">
              <span className="font-semibold">Open Findings by kind: </span>
              {(Object.entries(summary.finding_counts_by_category) as [Category, number][]).map(([category, count], i) => (
                <span key={category}>
                  {i > 0 && ", "}
                  {CATEGORY_NAME[category].toLowerCase()} <span className="font-mono">{count}</span>
                </span>
              ))}
              .
            </p>
          </div>
        </div>
      </details>

      <FindingDrawer findingId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
