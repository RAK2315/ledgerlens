"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { percent } from "@/lib/format";
import type { EvalReport } from "@/lib/types";
import { ErrorState, PageTitle, Pill, Skeleton } from "@/components/ui";

export default function ProofPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    api.evalReport().then(setReport).catch((e: Error) => setError(e.message));
  };
  useEffect(load, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!report)
    return (
      <div className="grid gap-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-96" />
      </div>
    );

  const rows = [...report.rows].filter((r) => r.planted > 0).sort((a, b) => (a.source === b.source ? (b.catch_rate ?? 0) - (a.catch_rate ?? 0) || b.planted - a.planted : a.source === "ml" ? -1 : 1));
  const planted = rows.reduce((s, r) => s + r.planted, 0);
  const caught = rows.reduce((s, r) => s + r.caught, 0);
  const reported = report.rows.reduce((s, r) => s + r.reported, 0);
  const falseAlarms = report.rows.reduce((s, r) => s + r.false_alarms, 0);
  const onTraps = report.rows.reduce((s, r) => s + r.on_benign_traps, 0);

  return (
    <div>
      <PageTitle
        title="Proof"
        lead="The data has mistakes planted on purpose and a list of every one. These numbers are for February and March 2026, months the matchers never trained on."
        right={<Pill tone="ok">Test split: Feb and Mar 2026</Pill>}
      />

      <div className="mb-4 grid grid-cols-3 gap-4">
        <div className="card p-4">
          <p className="font-semibold text-ink-2">Catch rate</p>
          <p className="font-display text-[34px] font-extrabold leading-tight text-ok">{percent(caught / planted, 1)}</p>
          <p className="text-[13px] text-ink-3">
            {caught.toLocaleString("en-IN")} of {planted.toLocaleString("en-IN")} planted errors and true matches found
          </p>
        </div>
        <div className="card p-4">
          <p className="font-semibold text-ink-2">False alarm rate</p>
          <p className="font-display text-[34px] font-extrabold leading-tight">{percent(falseAlarms / reported, 1)}</p>
          <p className="text-[13px] text-ink-3">
            {falseAlarms} of {reported.toLocaleString("en-IN")} reported items were not planted
          </p>
        </div>
        <div className="card p-4">
          <p className="font-semibold text-ink-2">Findings on Benign traps</p>
          <p className="font-display text-[34px] font-extrabold leading-tight">{onTraps}</p>
          <p className="text-[13px] text-ink-3">Records that look wrong but are fine: part payments, bundled payments, rounding</p>
        </div>
      </div>

      <section className="card p-5">
        <h2 className="mb-1 font-display text-lg font-bold">Catch rate per Finding type</h2>
        <p className="mb-3 text-[13px] text-ink-3">Bars show the share of planted errors found. The matcher rows are the two trained models; the rest are rules.</p>
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line text-right text-ink-3">
              <th className="px-3 py-2 text-left font-semibold">Finding type</th>
              <th className="w-[34%] px-3 py-2 text-left font-semibold">Catch rate</th>
              <th className="px-3 py-2 font-semibold">Planted</th>
              <th className="px-3 py-2 font-semibold">Caught</th>
              <th className="px-3 py-2 font-semibold">False alarms</th>
              <th className="px-3 py-2 font-semibold">False alarm rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.finding_type} className="border-b border-line-2 text-right">
                <td className="px-3 py-2 text-left">
                  {row.label} {row.source === "ml" && <Pill tone="miss">trained model</Pill>}
                </td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="h-3 flex-1 rounded-full bg-line-2">
                      <span className={`block h-full rounded-full ${(row.catch_rate ?? 0) >= 0.9 ? "bg-ok" : "bg-dup"}`} style={{ width: `${(row.catch_rate ?? 0) * 100}%` }} />
                    </span>
                    <span className="w-12 font-mono font-semibold">{percent(row.catch_rate)}</span>
                  </span>
                </td>
                <td className="px-3 py-2 font-mono">{row.planted}</td>
                <td className="px-3 py-2 font-mono">{row.caught}</td>
                <td className="px-3 py-2 font-mono">{row.false_alarms}</td>
                <td className="px-3 py-2 font-mono">{percent(row.false_alarm_rate, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-[13px] text-ink-2">
          One note on the labels: the dataset marks purchase invoices left unpaid as fine. LedgerLens reports them once they pass 180 days, because the credit is then at risk, and
          scores that rule against its own labels. The data is synthetic, so real books will be harder than this.
        </p>
      </section>
    </div>
  );
}
