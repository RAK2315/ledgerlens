"use client";

import { date, periodName, rupees, rupeesShort } from "@/lib/format";
import type { RingStep, RingStory as Story } from "@/lib/types";
import { Heading } from "./ui";

const LANES = { customer: 120, company: 400, supplier: 680 };
const ROW = 62;
const TOP = 78;

function when(step: RingStep): string {
  if (!step.until || step.until === step.date) return date(step.date);
  return `${date(step.date).replace(/ \d{4}$/, "")} to ${date(step.until)}`;
}

function arrowLabel(step: RingStep): string {
  const what = { purchase: "Purchases", sale: "Sales", out: "Out, no invoice", back: "Back, no invoice" }[step.kind];
  return `${what}: ${rupees(step.amount_paise)}, ${when(step)}`;
}

/** The month's money through a ring as dated arrows between the Customer, the Company and the Supplier. */
function Lanes({ story }: { story: Story }) {
  const height = TOP + story.steps.length * ROW + 70;
  const bottom = TOP + story.steps.length * ROW;
  return (
    <svg viewBox={`0 0 800 ${height}`} className="w-full" role="img" aria-label={`Money between you, ${story.supplier.name} and ${story.customer.name}: ${story.steps.map((s) => s.text).join(" ")}`}>
      {(
        [
          [LANES.customer, story.customer.name, "your customer"],
          [LANES.company, "You", "the company"],
          [LANES.supplier, story.supplier.name, "your supplier"],
        ] as const
      ).map(([x, name, role]) => (
        <g key={role}>
          <text x={x} y={24} textAnchor="middle" className="fill-ink font-display text-[19px] font-bold">
            {name}
          </text>
          <text x={x} y={44} textAnchor="middle" className="fill-ink-2 text-[13px]">
            {role}
          </text>
          <line x1={x} y1={56} x2={x} y2={bottom} stroke="var(--line)" strokeWidth="2" />
        </g>
      ))}
      {story.steps.map((step, i) => {
        const y = TOP + i * ROW + 34;
        const [from, to] =
          step.kind === "sale" ? [LANES.customer, LANES.company] : step.kind === "back" ? [LANES.supplier, LANES.company] : [LANES.company, LANES.supplier];
        const round = step.kind === "out" || step.kind === "back";
        const colour = round ? "var(--bad)" : "var(--ink)";
        const tip = to > from ? -1 : 1;
        return (
          <g key={`${step.kind}-${step.date}`}>
            <text x={(from + to) / 2} y={y - 10} textAnchor="middle" className={`text-[14px] font-semibold ${round ? "fill-bad" : "fill-ink"}`}>
              {arrowLabel(step)}
            </text>
            <line x1={from} y1={y} x2={to + tip * 4} y2={y} stroke={colour} strokeWidth="2.5" strokeDasharray={round ? "7 5" : undefined} />
            <polygon points={`${to},${y} ${to + tip * 13},${y - 6} ${to + tip * 13},${y + 6}`} fill={colour} />
            <circle cx={from} cy={y} r="4" fill={colour} />
          </g>
        );
      })}
      <path d={`M ${LANES.customer} ${bottom} v 26 H ${LANES.supplier} v -26`} fill="none" stroke="var(--bad)" strokeWidth="2.5" strokeDasharray="7 5" />
      <text x={LANES.company} y={bottom + 50} textAnchor="middle" className="fill-bad text-[14px] font-semibold">
        Same PAN {story.pan}: one owner on both sides
      </text>
    </svg>
  );
}

export function RingStory({ story, period, creditAtRisk }: { story: Story; period: string; creditAtRisk: number }) {
  const tallest = Math.max(1, ...story.timeline.map((m) => m.credit_paise));
  const yearCredit = story.timeline.reduce((sum, m) => sum + m.credit_paise, 0);
  return (
    <>
      <section className="px-2">
        <Heading note={periodName(period)}>Follow the money</Heading>
        <div className="mt-6 grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] items-start gap-12">
          <Lanes story={story} />
          <ol className="grid gap-0">
            {story.steps.map((step, i) => (
              <li key={`${step.kind}-${step.date}`} className="grid grid-cols-[32px_1fr] gap-3 border-b border-line py-3 first:pt-0">
                <span className={`font-display text-[22px] font-bold leading-none ${step.kind === "out" || step.kind === "back" ? "text-bad" : "text-ink-3"}`}>{i + 1}</span>
                <span>
                  <span className="block text-[16px] font-semibold leading-snug">{step.text}</span>
                  <span className="mt-0.5 block text-[14px] text-ink-2">
                    {when(step)} · <span className="font-mono text-[13px]">{step.records.slice(0, 3).join(", ")}</span>
                    {step.records.length > 3 && ` and ${step.records.length - 3} more`}
                  </span>
                </span>
              </li>
            ))}
            <li className="grid grid-cols-[32px_1fr] gap-3 py-3">
              <span className="font-display text-[22px] font-bold leading-none text-bad">{story.steps.length + 1}</span>
              <span>
                <span className="block text-[16px] font-semibold leading-snug">
                  {story.supplier.name} and {story.customer.name} carry the same PAN, so one owner is your Supplier and your Customer.
                </span>
                <span className="mt-0.5 block text-[14px] text-ink-2">{rupees(creditAtRisk)} of credit this month depends on purchases from them.</span>
              </span>
            </li>
          </ol>
        </div>
      </section>

      <section className="px-2">
        <Heading note={`${rupeesShort(yearCredit)} of credit over the year`}>The ring across the year</Heading>
        <ol className="mt-8 grid grid-cols-12 items-end gap-3" aria-label="Credit depending on the ring in each month">
          {story.timeline.map((m) => (
            <li key={m.period} className="flex flex-col items-center gap-1.5">
              <span className="font-mono text-[13px]">{rupeesShort(m.credit_paise).replace("Rs ", "")}</span>
              <span className={`w-full rounded-bar ${m.period === period ? "bg-orange-deep" : "bg-orange/50"}`} style={{ height: `${Math.max(3, (m.credit_paise / tallest) * 140)}px` }} />
              <span className={`text-[14px] ${m.period === period ? "font-bold" : "font-semibold"}`}>{periodName(m.period).slice(0, 3)}</span>
              <span className="h-4 text-[12px] font-semibold text-bad">{m.round_trip ? "round trip" : ""}</span>
            </li>
          ))}
        </ol>
        <p className="mt-3 max-w-[100ch] text-[14px] text-ink-2">
          Bars are the tax on purchases from {story.supplier.name} in each month, in rupees: the credit that depends on the ring. They traded with you in{" "}
          {story.timeline.filter((m) => m.bought_paise > 0 || m.sold_paise > 0).length} of 12 months. A month marked round trip has money that went out and came back with no invoice.
        </p>
      </section>
    </>
  );
}
