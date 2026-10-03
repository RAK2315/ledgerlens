"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { BadgeCheck, LayoutDashboard, ListChecks, Network, Scale, Search, Zap } from "lucide-react";
import { useRun } from "@/lib/run-store";
import { periodName } from "@/lib/format";
import { ErrorState, Skeleton } from "./ui";
import { RunOverlay } from "./RunOverlay";
import { DemoGuide } from "./DemoGuide";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/workbench", label: "Workbench", icon: ListChecks },
  { href: "/graph", label: "Ring view", icon: Network },
  { href: "/liability", label: "Liability", icon: Scale },
  { href: "/proof", label: "Proof", icon: BadgeCheck },
];

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <span className={`flex size-10 items-center justify-center rounded-xl ${dark ? "bg-ink text-cream" : "bg-white/10 text-white"}`} aria-hidden>
      <Search className="size-5" strokeWidth={2.6} />
    </span>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const run = useRun();
  const busy = run.runState === "loading" || run.runState === "running";

  useEffect(() => {
    if (run.ready && !run.loadError && !run.runId && !busy) router.replace("/");
  }, [run.ready, run.loadError, run.runId, busy, router]);

  return (
    <div className="flex min-h-screen">
      <nav aria-label="Main" className="sticky top-0 flex h-screen w-[84px] shrink-0 flex-col items-center gap-1 bg-side py-4">
        <Link href="/" aria-label="LedgerLens start" className="mb-4">
          <Logo />
        </Link>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex w-[68px] flex-col items-center gap-1 rounded-xl py-2.5 text-[11px] font-semibold ${
                active ? "bg-orange/20 text-orange" : "text-white/60 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="size-5" aria-hidden />
              {label}
            </Link>
          );
        })}
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
                className="rounded-[9px] border border-line bg-paper px-2.5 py-2 font-mono text-[13px]"
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
    </div>
  );
}
