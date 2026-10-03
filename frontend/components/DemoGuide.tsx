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
    <div data-guide className="fixed bottom-0 left-[152px] right-0 z-30 border-t-2 border-ink bg-paper">
      <div className="flex items-center gap-6 px-8 py-3">
        <p className="font-display text-[26px] font-extrabold leading-none">
          {index + 1}
          <span className="text-ink-3"> / {steps.length}</span>
        </p>
        <ol className="flex gap-1" aria-hidden>
          {steps.map((s, i) => (
            <li key={s.path} className={`h-1.5 w-7 rounded-bar ${i <= index ? "bg-orange-deep" : "bg-line"}`} />
          ))}
        </ol>
        <p className="min-w-0 flex-1 text-[15px] leading-snug">
          <span className="font-display text-[18px] font-bold">{step.title}.</span> <span className="text-ink-2">{step.say}</span>
        </p>
        <button className="btn" onClick={() => go(index - 1)} disabled={index === 0}>
          <ArrowLeft className="size-4" aria-hidden /> Back
        </button>
        <button className="btn btn-primary" onClick={() => go(index + 1)} disabled={index === steps.length - 1}>
          {index === steps.length - 1 ? "End of the walk-through" : `Next: ${steps[index + 1].title}`} <ArrowRight className="size-4" aria-hidden />
        </button>
      </div>
    </div>
  );
}
