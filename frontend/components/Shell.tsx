"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Calculator, FileSpreadsheet, IndianRupee, Rows3, ScrollText, Target, Waypoints, Zap } from "lucide-react";
import { useRun } from "@/lib/run-store";
import { periodName } from "@/lib/format";
import { ErrorState, Skeleton } from "./ui";
import { RunLog, RunOverlay } from "./RunOverlay";
import { DemoGuide } from "./DemoGuide";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: IndianRupee },
  { href: "/workbench", label: "Workbench", icon: Rows3 },
  { href: "/graph", label: "Ring view", icon: Waypoints },
  { href: "/liability", label: "Liability", icon: Calculator },
  { href: "/proof", label: "Proof", icon: Target },
  { href: "/data", label: "Data", icon: FileSpreadsheet },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const run = useRun();
  const busy = run.runState === "loading" || run.runState === "running";
  const [logOpen, setLogOpen] = useState(false);
  const closeLog = useCallback(() => setLogOpen(false), []);

  useEffect(() => {
    if (run.ready && !run.loadError && !run.runId && !busy) router.replace("/");
  }, [run.ready, run.loadError, run.runId, busy, router]);

  return (
    <div className="flex min-h-screen">
      <nav aria-label="Main" className="sticky top-0 flex h-screen w-[152px] shrink-0 flex-col bg-side">
        <Link href="/" className="flex h-[72px] items-center border-b border-white/10 px-5 font-display text-[22px] font-extrabold leading-none text-cream hover:text-white">
          LedgerLens
        </Link>
        <div className="mt-4 grid">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2.5 border-l-[3px] py-2.5 pl-[17px] pr-3 text-[15px] font-semibold ${
                  active ? "border-orange text-white" : "border-transparent text-white/55 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon className={`size-[17px] shrink-0 ${active ? "text-orange" : ""}`} strokeWidth={1.75} aria-hidden />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-between gap-6 border-b border-line bg-paper px-6 py-3">
          <div>
            <p className="font-display text-[22px] font-bold leading-tight">{run.dataset?.company.name ?? "LedgerLens"}</p>
            <p className="font-mono text-[13px] text-ink-3">
              {run.dataset?.company.gstin}
              {run.summary && ` · ${periodName(run.summary.period)} · ${run.summary.invoice_count.toLocaleString("en-IN")} invoices`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-[13px] text-ink-2">
              Return period
              <select
                className="rounded-control border border-line bg-paper px-2.5 py-2 font-mono text-[13px]"
                value={run.target}
                disabled={busy || !run.dataset}
                onChange={(e) => run.choosePeriod(e.target.value)}
              >
                {(run.dataset?.periods ?? [run.period]).map((p) => (
                  <option key={p} value={p}>
                    {periodName(p)}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn" disabled={busy || !run.runId} onClick={() => setLogOpen(true)}>
              <ScrollText className="size-4" aria-hidden />
              Run log
            </button>
            <button className="btn btn-primary" disabled={busy || !run.dataset} onClick={() => run.launch()}>
              <Zap className="size-4" aria-hidden />
              Run reconciliation
            </button>
          </div>
        </header>

        <main className={`mx-auto max-w-[1440px] p-6 ${process.env.NEXT_PUBLIC_DEMO === "1" ? "pb-24" : ""}`}>
          {!run.ready ? (
            <div className="grid gap-4">
              <Skeleton className="h-10 w-80" />
              <Skeleton className="h-28" />
              <Skeleton className="h-64" />
            </div>
          ) : run.loadError ? (
            <ErrorState message={run.loadError} onRetry={run.retry} />
          ) : (
            children
          )}
        </main>
      </div>

      {process.env.NEXT_PUBLIC_DEMO === "1" && run.runId && !busy && <DemoGuide />}

      <RunOverlay />
      {logOpen && run.runId && run.summary && !busy && <RunLog runId={run.runId} period={run.summary.period} onClose={closeLog} />}
    </div>
  );
}
