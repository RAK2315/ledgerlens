"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { IMPACT_WORDS, date, periodName, rupees, rupeesShort } from "@/lib/format";
import type { Category, FindingRow, Liability, Summary } from "@/lib/types";
import { FindingDrawer } from "@/components/FindingDrawer";
import { CATEGORY_NAME, EmptyState, Skeleton } from "@/components/ui";

const CATEGORY_NOTE: Record<Category, string> = {
  missing: "not in GSTR-2B, books or bank",
  tax: "rate, tax type or arithmetic",
  anomaly: "unusual, each with a reason",
  matching: "amount, date or number differs",
  duplicate: "entered, booked or paid twice",
  filing: "the filed return",
};

function Heading({ children, note }: { children: React.ReactNode; note?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b-2 border-ink pb-3">
      <h2 className="font-display text-[28px] font-bold leading-tight">{children}</h2>
      {note && <span className="text-[14px] text-ink-2">{note}</span>}
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
  const matched = ((c.auto + c.one_to_many) / total) * 100;
  const radius = 54;
  const around = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <div className="flex items-center gap-10">
      <svg viewBox="0 0 140 140" className="size-52 shrink-0 -rotate-90" role="img" aria-label={`${matched.toFixed(1)} percent of matches needed no one`}>
        {parts.map((p) => {
          const length = (p.value / total) * around;
          const arc = <circle key={p.label} cx="70" cy="70" r={radius} fill="none" stroke={p.colour} strokeWidth="16" strokeDasharray={`${length} ${around - length}`} strokeDashoffset={-offset} />;
          offset += length;
          return arc;
        })}
        <text x="70" y="70" textAnchor="middle" transform="rotate(90 70 70)" className="fill-ink font-display text-[26px] font-extrabold">
          {matched.toFixed(1)}%
        </text>
        <text x="70" y="86" textAnchor="middle" transform="rotate(90 70 70)" className="fill-ink-2 text-[9px]">
          needed no one
        </text>
      </svg>
      <ul className="grid flex-1 gap-3">
        {parts.map((p) => (
          <li key={p.label} className="flex items-baseline gap-3 border-b border-line-2 pb-3 last:border-b-0">
            <span className="size-3 shrink-0 translate-y-[1px] rounded-full" style={{ background: p.colour }} aria-hidden />
            <span className="text-[16px]">{p.label}</span>
            <span className="ml-auto font-display text-[24px] font-bold leading-none">{p.value.toLocaleString("en-IN")}</span>
          </li>
        ))}
        <li className="text-[14px] text-ink-2">{c.open} invoices are open (not yet due or unpaid), which is normal.</li>
      </ul>
    </div>
  );
}

function TaxTypes({ liability }: { liability: Liability }) {
  const largest = Math.max(1, ...liability.by_tax_type.map((t) => t.output_paise));
  return (
    <ul className="grid gap-5">
      {liability.by_tax_type.map((t) => (
        <li key={t.tax_type} className="grid grid-cols-[64px_1fr_120px] items-center gap-4">
          <span className="font-display text-[22px] font-bold uppercase">{t.tax_type}</span>
          <span className="grid gap-1.5">
            <span className="flex items-center gap-3">
              <span className="h-3 rounded-full bg-ink" style={{ width: `${(t.output_paise / largest) * 100}%` }} />
              <span className="whitespace-nowrap font-mono text-[13px]">{rupeesShort(t.output_paise)} output</span>
            </span>
            <span className="flex items-center gap-3">
              <span className="h-3 rounded-full bg-ok" style={{ width: `${Math.max(1, (t.eligible_itc_paise / largest) * 100)}%` }} />
              <span className="whitespace-nowrap font-mono text-[13px]">{rupeesShort(t.eligible_itc_paise)} credit</span>
            </span>
          </span>
          <span className="text-right">
            <span className="block font-display text-[24px] font-bold leading-none">{rupeesShort(t.net_paise)}</span>
            <span className="text-[13px] text-ink-2">to pay</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
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
      <div className="grid gap-8">
        <Skeleton className="h-72 rounded-[20px]" />
        <div className="grid grid-cols-[7fr_5fr] gap-12">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );

  const c = summary.match_counts;
  const openFindings = summary.finding_counts_by_status.open ?? 0;
  const largestCause = Math.max(1, ...summary.itc_at_risk_by_cause.map((x) => x.paise));
  const first = summary.top_findings[0];
  const kinds = (Object.entries(summary.finding_counts_by_category) as [Category, number][]).sort((a, b) => b[1] - a[1]);
  const largestKind = Math.max(1, ...kinds.map(([, n]) => n));
  const declared = liability?.declared;
  const filedWidth = declared ? Math.min(100, (declared.net_paise / Math.max(declared.net_paise, summary.net_payable_paise)) * 100) : 0;
  const computedWidth = declared ? Math.min(100, (summary.net_payable_paise / Math.max(declared.net_paise, summary.net_payable_paise)) * 100) : 0;

  return (
    <div className="grid gap-12 pb-6">
      <section className="grid grid-cols-[minmax(0,1fr)_380px] gap-10 rounded-[20px] bg-side px-10 py-9 text-cream">
        <div>
          <p className="text-[15px] text-cream/70">
            {periodName(summary.period)} · {summary.invoice_count.toLocaleString("en-IN")} invoices checked against the ledger, the bank statement and GSTR-2B
          </p>
          <h1 className="mt-3 max-w-[18ch] font-display text-[54px] font-extrabold leading-[1.02] tracking-[-0.02em]">
            {summary.itc_at_risk_paise > 0 ? (
              <>
                <span className="text-orange">{rupeesShort(summary.itc_at_risk_paise)}</span> of tax credit is at risk this month.
              </>
            ) : (
              "No tax credit is at risk this month."
            )}
          </h1>
          <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-4">
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

        <div className="flex flex-col justify-between border-l border-white/15 pl-10">
          {first ? (
            <>
              <div>
                <p className="text-[15px] font-semibold text-orange">Start here</p>
                <p className="mt-2 font-display text-[24px] font-bold leading-snug">{first.title}</p>
                <p className="mt-2 text-[15px] text-cream/70">The evidence, the rule and a drafted fix are ready to review.</p>
              </div>
              <button onClick={() => setOpenId(first.id)} className="btn btn-primary mt-6 self-start px-5 py-3 text-[15px]">
                See why and fix <ArrowRight className="size-4" aria-hidden />
              </button>
            </>
          ) : (
            <div>
              <p className="text-[15px] font-semibold text-orange">All clear</p>
              <p className="mt-2 font-display text-[24px] font-bold leading-snug">Every Finding has been approved or dismissed.</p>
            </div>
          )}
        </div>
      </section>

      {rateChange.length > 0 && (
        <button onClick={() => setOpenId(rateChange[0].id)} className="group -my-5 flex w-full items-center gap-4 px-2 text-left text-[16px]">
          <span className="size-2.5 shrink-0 rounded-full bg-bad" aria-hidden />
          <span className="flex-1">
            <b>
              {rateChange.length} {rateChange.length === 1 ? "invoice" : "invoices"} this month still {rateChange.length === 1 ? "uses" : "use"} a GST rate that ended on 22 Sep 2025.
            </b>{" "}
            {rupees(rateChange.reduce((sum, f) => sum + f.impact_paise, 0))} in all. Largest: <span className="font-mono text-[14px]">{rateChange[0].record_refs[0]?.id}</span>.
          </span>
          <span className="inline-flex items-center gap-1 font-semibold text-orange-deep group-hover:underline">
            See why and fix <ArrowRight className="size-4" aria-hidden />
          </span>
        </button>
      )}

      <div className="grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] gap-12 px-2">
        <section>
          <Heading note={`${summary.top_findings.length} largest of ${openFindings} open Findings`}>Fix these first</Heading>
          {summary.top_findings.length === 0 ? (
            <EmptyState title="No open Findings in this period" hint="Every Finding has been approved or dismissed." />
          ) : (
            <ol>
              {summary.top_findings.map((f, i) => (
                <li key={f.id} className="border-b border-line">
                  <button onClick={() => setOpenId(f.id)} className="group grid w-full grid-cols-[28px_150px_1fr_auto] items-center gap-4 py-4 text-left hover:bg-cream-2">
                    <span className="pl-1 font-display text-[20px] font-bold text-ink-3">{i + 1}</span>
                    <span className="font-display text-[26px] font-bold leading-none">{f.impact_type === "none" ? "" : rupees(f.impact_paise)}</span>
                    <span>
                      <span className="text-[16px] font-semibold">{f.label}</span>
                      <span className="block text-[14px] text-ink-2">
                        {f.party?.name ?? "Company"}, <span className="font-mono text-[13px]">{f.record_refs[0]?.id}</span>, {IMPACT_WORDS[f.impact_type]}
                        {f.deadline ? `, due ${date(f.deadline)}` : ""}
                      </span>
                    </span>
                    <ArrowRight className="mr-2 size-5 text-orange-deep transition-transform group-hover:translate-x-1" aria-hidden />
                  </button>
                </li>
              ))}
            </ol>
          )}
          <Link href="/workbench" className="mt-4 inline-flex items-center gap-1 text-[16px] font-semibold text-orange-deep hover:underline">
            All {openFindings} Findings in the workbench <ArrowRight className="size-4" aria-hidden />
          </Link>
        </section>

        <section>
          <Heading note="each invoice counted once">Why credit is at risk</Heading>
          {summary.itc_at_risk_by_cause.length === 0 ? (
            <EmptyState title="No ITC at risk in this period" />
          ) : (
            <ol className="mt-5 grid gap-4">
              {summary.itc_at_risk_by_cause.map((cause) => (
                <li key={cause.finding_type}>
                  <div className="flex items-baseline justify-between gap-4 text-[15px]">
                    <span>{cause.label}</span>
                    <span className="font-mono font-semibold">{rupees(cause.paise)}</span>
                  </div>
                  <div className="mt-1.5 h-2.5 rounded-full bg-line-2">
                    <div className="h-full rounded-full bg-orange" style={{ width: `${Math.max(1.5, (cause.paise / largestCause) * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <div className="grid grid-cols-2 gap-12 px-2">
        <section>
          <Heading note={`${(c.auto + c.one_to_many + c.review + c.unmatched).toLocaleString("en-IN")} matches`}>How the month matched</Heading>
          <div className="mt-6">
            <Donut summary={summary} />
          </div>
        </section>

        <section>
          <Heading note={`${openFindings} open`}>Findings by kind</Heading>
          <ol className="mt-5 grid gap-3.5">
            {kinds.map(([category, count]) => (
              <li key={category} className="grid grid-cols-[110px_1fr] items-center gap-4">
                <span className="text-[16px] font-semibold">{CATEGORY_NAME[category]}</span>
                <span className="flex items-center gap-3">
                  <span className="h-6 rounded-[5px] bg-ink" style={{ width: `${Math.max(1, (count / largestKind) * 50)}%` }} />
                  <span className="font-display text-[22px] font-bold leading-none">{count}</span>
                  <span className="truncate text-[14px] text-ink-2">{CATEGORY_NOTE[category]}</span>
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {liability && (
        <div className="grid grid-cols-2 gap-12 px-2">
          <section>
            <Heading note="output tax against eligible credit">What the month should cost</Heading>
            <div className="mt-6">
              <TaxTypes liability={liability} />
            </div>
          </section>

          {declared && (
            <section>
              <Heading note={`return filed ${date(declared.filed_on)}`}>The filed return against LedgerLens</Heading>
              <div className="mt-6 grid gap-5">
                <div>
                  <div className="flex items-baseline justify-between text-[16px]">
                    <span>The filed return declared</span>
                    <span className="font-display text-[24px] font-bold leading-none">{rupeesShort(declared.net_paise)}</span>
                  </div>
                  <div className="mt-2 h-3 rounded-full bg-ink-3" style={{ width: `${filedWidth}%` }} />
                </div>
                <div>
                  <div className="flex items-baseline justify-between text-[16px]">
                    <span>LedgerLens works out</span>
                    <span className="font-display text-[24px] font-bold leading-none">{rupeesShort(summary.net_payable_paise)}</span>
                  </div>
                  <div className="mt-2 h-3 rounded-full bg-ink" style={{ width: `${computedWidth}%` }} />
                </div>
                {liability.gap_paise !== null && (
                  <p className="text-[16px]">
                    <span className="font-display text-[24px] font-bold text-orange-deep">{rupees(Math.abs(liability.gap_paise))}</span>{" "}
                    {liability.gap_paise >= 0 ? "more to pay than the return said." : "less to pay than the return said."}
                  </p>
                )}
                <Link href="/liability" className="inline-flex items-center gap-1 text-[16px] font-semibold text-orange-deep hover:underline">
                  See the working by tax type <ArrowRight className="size-4" aria-hidden />
                </Link>
              </div>
            </section>
          )}
        </div>
      )}

      <FindingDrawer findingId={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}
