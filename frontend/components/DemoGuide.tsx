"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";

type Step = { path: string; title: string; say: string };

/** The presenter's next-step control, shown when NEXT_PUBLIC_DEMO=1. It walks the demo journey in order. */
export function DemoGuide() {
  const { runId } = useRun();
  const router = useRouter();
  const pathname = usePathname();
  const [steps, setSteps] = useState<Step[]>([]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    Promise.all([api.findings(runId, { finding_type: "WRONG_TAX_RATE", page_size: 50 }), api.findings(runId, { finding_type: "MISSING_IN_2B", page_size: 1 })])
      .then(([rate, missing]) => {
        if (cancelled) return;
        const hero = rate.items.find((f) => f.title.includes(" since ")) ?? rate.items[0];
        const supplier = missing.items[0];
        setSteps(
          [
            { path: "/dashboard", title: "The month, in rupees", say: "ITC at risk, ITC found and Net payable first; then what caused them." },
            hero && { path: `/findings/${hero.id}`, title: "A Finding with its evidence", say: "The invoice, what it should be, the rule, and a drafted fix. Approve it and the numbers move." },
            supplier && { path: `/findings/${supplier.id}`, title: "Credit at risk at a Supplier", say: "The Supplier has not reported the invoice. The draft asks them to." },
            { path: "/workbench?view=one-to-many", title: "Matched, not flagged", say: "One payment settling several invoices is recognised and left alone." },
            { path: "/graph", title: "Supplier ring", say: "A Supplier and a Customer with one owner, a round trip of money, and a cancelled GSTIN." },
            { path: "/liability", title: "What the month should cost", say: "Net payable by tax type against the filed return." },
            { path: "/proof", title: "Measured on unseen months", say: "Catch rate and false alarms per Finding type." },
          ].filter(Boolean) as Step[],
        );
      })
      .catch(() => setSteps([]));
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    const at = steps.findIndex((s) => s.path.split("?")[0] === pathname);
    if (at >= 0) setIndex(at);
  }, [pathname, steps]);

  if (steps.length === 0) return null;
  const step = steps[index];
  const go = (to: number) => {
    setIndex(to);
    router.push(steps[to].path);
  };
  return (
    <div className="fixed bottom-4 left-1/2 z-30 flex w-[min(760px,calc(100vw-140px))] -translate-x-1/2 items-center gap-3 rounded-xl bg-ink px-4 py-2.5 text-cream shadow-float">
      <span className="rounded-full bg-white/10 px-2.5 py-0.5 font-mono text-[12px]">
        {index + 1}/{steps.length}
      </span>
      <p className="min-w-0 flex-1 text-[13px]">
        <b className="text-white">{step.title}.</b> <span className="text-cream/80">{step.say}</span>
      </p>
      <button className="rounded-lg p-1.5 hover:bg-white/10 disabled:opacity-30" onClick={() => go(index - 1)} disabled={index === 0} aria-label="Previous step">
        <ArrowLeft className="size-4" aria-hidden />
      </button>
      <button
        className="flex items-center gap-1.5 rounded-lg bg-orange-deep px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-40"
        onClick={() => go(index + 1)}
        disabled={index === steps.length - 1}
      >
        Next <ArrowRight className="size-4" aria-hidden />
      </button>
    </div>
  );
}
