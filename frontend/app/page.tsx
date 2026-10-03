"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, FileSearch, IndianRupee, MailCheck, Network, Play, Target } from "lucide-react";
import { useRun } from "@/lib/run-store";
import { Logo } from "@/components/Shell";
import { StageStepper } from "@/components/StageStepper";
import { ErrorState } from "@/components/ui";

const SOURCES = ["Invoices", "Books (ledger)", "Bank statement", "GSTR-2B (what suppliers reported)"];
const POINTS = [
  { icon: IndianRupee, title: "Rupees first", text: "Every mismatch is priced: credit at risk, credit you can still claim, tax charged too high or too low." },
  { icon: FileSearch, title: "Evidence for every Finding", text: "The two records side by side, the rule that applies and the reason in plain words." },
  { icon: MailCheck, title: "A fix you approve", text: "A draft supplier email, credit note or ledger entry. Nothing leaves without your approval." },
  { icon: Network, title: "Supplier rings", text: "Suppliers and Customers that share one owner, and money that goes out and comes back." },
  { icon: Target, title: "Measured, not claimed", text: "Catch rate and false alarms on months the system never saw." },
];

export default function StartPage() {
  const run = useRun();
  const router = useRouter();
  const busy = run.runState === "loading" || run.runState === "running";
  const started = busy || run.runState === "failed" || run.stages.length > 0;

  async function start() {
    if (await run.launch()) router.push("/dashboard");
  }

  return (
    <div className="min-h-screen bg-cream">
      <div className="mx-auto grid max-w-[1280px] gap-10 px-8 py-10 lg:grid-cols-[1.15fr_1fr] lg:items-start">
        <section>
          <div className="mb-8 flex items-center gap-3">
            <Logo dark />
            <span className="font-display text-2xl font-extrabold">LedgerLens</span>
          </div>
          <h1 className="font-display text-[44px] font-extrabold leading-[1.05]">
            Your GST records disagree. <span className="text-orange-deep">LedgerLens tells you what it costs, why, and how to fix it.</span>
          </h1>
          <p className="mt-4 max-w-xl text-[16px] leading-relaxed text-ink-2">
            Every month a business must make four records agree. When they do not, input tax credit is lost or tax is overpaid, and today that is found
            late, by hand, in spreadsheets.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {SOURCES.map((s) => (
              <span key={s} className="rounded-full border border-line bg-cream-2 px-3 py-1 text-[13px] font-semibold">
                {s}
              </span>
            ))}
          </div>

          <ul className="mt-8 grid gap-3 sm:grid-cols-2">
            {POINTS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3 rounded-xl border border-line bg-cream-2 p-3.5">
                <Icon className="mt-0.5 size-5 shrink-0 text-orange-deep" aria-hidden />
                <div>
                  <p className="font-semibold">{title}</p>
                  <p className="text-[13px] text-ink-2">{text}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-[13px] text-ink-2">
            <b className="text-ink">Code decides every number.</b> Tested rules and two trained matchers do the work. The language model only words the
            explanation and the draft.
          </p>
        </section>

        <section className="card p-6 shadow-float">
          <p className="font-display text-2xl font-bold">Reconcile one month, end to end</p>
          <p className="mt-1 text-ink-2">
            Demo company: Sharma Traders Pvt Ltd, Delhi. September 2025, the month the GST rates changed (22 Sep 2025).
          </p>

          {run.loadError && (
            <div className="mt-4">
              <ErrorState message={run.loadError} onRetry={run.retry} />
            </div>
          )}

          {!started ? (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button className="btn btn-primary px-5 py-3 text-[15px]" onClick={start} disabled={!run.ready || !!run.loadError}>
                <Play className="size-4" aria-hidden />
                {run.runId ? "Run again" : "Load demo company"}
              </button>
              {run.runId && (
                <Link href="/dashboard" className="btn px-5 py-3 text-[15px]">
                  Open dashboard <ArrowRight className="size-4" aria-hidden />
                </Link>
              )}
            </div>
          ) : (
            <div className="mt-4">
              <StageStepper events={run.stages} waiting={busy} />
              {run.runState === "failed" && (
                <div className="mt-3">
                  <ErrorState message={run.runError ?? "The Run failed."} onRetry={start} />
                </div>
              )}
            </div>
          )}
          <p className="mt-5 border-t border-line-2 pt-4 text-[13px] text-ink-3">
            The data is one year of books for a made-up company, with mistakes put in on purpose and a list of every one of them, so results can be checked.
          </p>
        </section>
      </div>
    </div>
  );
}
