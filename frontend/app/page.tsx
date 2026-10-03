"use client";

import { FindingDemo, type DemoFinding } from "@/components/landing/FindingDemo";
import { ProofDemo, type DemoProof } from "@/components/landing/ProofDemo";
import { RunDemo } from "@/components/landing/RunDemo";
import { CauseBar, MoneyStrip } from "@/components/MoneyStrip";
import { RingStory } from "@/components/RingStory";
import { StartActions } from "@/components/StartActions";
import { IMPACT_WORDS, rupees } from "@/lib/format";
import type { FeedItem, ImpactType, RingStory as Story, StageEvent, Summary } from "@/lib/types";
// Real results for September 2025, written by scripts/landing-data.mjs. Nothing on this page is a picture.
import data from "@/lib/landing-data.json";

const WIDE = "mx-auto max-w-[1280px] px-10";
const H2 = "font-display text-[64px] font-extrabold leading-[0.98] tracking-[-0.025em]";
const LEAD = "mt-4 max-w-[58ch] text-[18px] leading-relaxed text-ink-2";

const summary = data.summary as unknown as Summary;
const top = data.summary.top_findings as { label: string; impact_paise: number; impact_type: ImpactType; party: string | null; record: string | null }[];
const count = (n: number) => n.toLocaleString("en-IN");

export default function StartPage() {
  return (
    <div className="min-h-screen bg-paper text-[16px]">
      <section className="bg-side text-cream">
        <header className={`flex items-center justify-between py-6 ${WIDE}`}>
          <span className="font-display text-[24px] font-extrabold">LedgerLens</span>
          <nav aria-label="Page" className="flex items-center gap-8 text-[15px] text-cream/75">
            <a href="#problem" className="hover:text-cream">The problem</a>
            <a href="#how" className="hover:text-cream">How it works</a>
            <a href="#fix" className="hover:text-cream">Try a fix</a>
            <a href="#ring" className="hover:text-cream">Supplier rings</a>
            <a href="#proof" className="hover:text-cream">Proof</a>
            <a href="#data" className="hover:text-cream">The data</a>
          </nav>
        </header>
        <div className={`pb-64 pt-16 ${WIDE}`}>
          <h1 className="max-w-[15ch] font-display text-[92px] font-extrabold leading-[0.94] tracking-[-0.03em]">
            Your GST records disagree. <span className="text-orange">See what it costs.</span>
          </h1>
          <p className="mt-7 max-w-[52ch] text-[20px] leading-relaxed text-cream/80">
            LedgerLens reconciles a month of books, prices every mismatch in rupees, shows the evidence and drafts the fix for you to approve.
          </p>
          <div className="mt-9">
            <StartActions onDark withOverlay />
          </div>
          <p className="mt-4 text-[15px] text-cream/60">Demo company: {data.company.name}, Delhi. September 2025, the month GST rates changed.</p>
        </div>
      </section>

      <div className={`-mt-52 ${WIDE}`}>
        <div className="rounded-surface bg-app-bg p-8 shadow-float">
          <div className="flex items-baseline justify-between gap-6">
            <p className="font-display text-[26px] font-extrabold leading-none">September 2025</p>
            <p className="text-[15px] text-ink-2">
              {count(summary.invoice_count)} invoices checked against the ledger, the bank statement and GSTR-2B · {summary.finding_counts_by_status.open} open Findings
            </p>
          </div>
          <div className="mt-4">
            <MoneyStrip money={summary} />
          </div>
          <div className="mt-8 grid grid-cols-[minmax(0,6fr)_minmax(0,5fr)] gap-12">
            <div>
              <p className="mb-4 border-b-2 border-ink pb-2 font-display text-[22px] font-bold">Why credit is at risk</p>
              <CauseBar causes={summary.itc_at_risk_by_cause} total={summary.itc_at_risk_paise} columns={2} />
            </div>
            <div>
              <p className="border-b-2 border-ink pb-2 font-display text-[22px] font-bold">Fix these first</p>
              <ol>
                {top.slice(0, 4).map((f, i) => (
                  <li key={`${f.record}-${i}`} className="grid grid-cols-[130px_1fr] items-baseline gap-4 border-b border-line py-3">
                    <span className="font-display text-[22px] font-bold leading-none">{rupees(f.impact_paise)}</span>
                    <span>
                      <span className="block text-[15px] font-semibold">{f.label}</span>
                      <span className="text-[13px] text-ink-2">
                        {f.party}, <span className="font-mono">{f.record}</span>, {IMPACT_WORDS[f.impact_type]}
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
        <p className="mt-3 text-center text-[14px] text-ink-2">The dashboard for the demo month. Everything on this page is the app itself with real results, not a picture.</p>
      </div>

      <section
        id="problem"
        className="scroll-mt-10 bg-cover bg-center py-28"
        style={{ backgroundImage: "linear-gradient(to bottom, var(--paper), transparent 25%, transparent 75%, var(--cream)), url(/landing-bg.png)" }}
      >
        <div className={WIDE}>
          <h2 className={`max-w-[18ch] ${H2}`}>Four records describe one purchase. They rarely agree.</h2>
          <div className="mt-12 grid grid-cols-4 gap-x-10">
            {[
              [count(data.counts.invoices), "invoices", "What was bought and sold, and the tax on each."],
              [count(data.counts.ledger_entries), "ledger entries", "What the accountant entered in the books."],
              [count(data.counts.bank_transactions), "bank lines", "What was actually paid and received."],
              [count(data.counts.gstr2b_lines), "GSTR-2B lines", "What your suppliers reported to the GST portal."],
            ].map(([big, unit, text]) => (
              <div key={unit} className="border-t-2 border-ink pt-4">
                <p className="font-display text-[48px] font-extrabold leading-none">{big}</p>
                <p className="mt-1 text-[16px] font-semibold">{unit}</p>
                <p className="mt-2 text-[16px] text-ink-2">{text}</p>
              </div>
            ))}
          </div>

          <div className="mt-16 grid grid-cols-2 items-start gap-x-16">
            <p className="max-w-[26ch] font-display text-[34px] font-bold leading-[1.15]">
              Where they differ, input tax credit is lost or tax is overpaid. In September 2025 that came to{" "}
              <span className="text-orange-deep">{rupees(summary.itc_at_risk_paise)}</span> of credit at risk.
            </p>
            <div>
              <p className="text-[16px] font-semibold">One example from that month</p>
              <dl className="mt-3 grid grid-cols-[120px_1fr] gap-x-6 text-[17px] leading-relaxed">
                <dt className="border-t border-line py-3 text-ink-2">In the books</dt>
                <dd className="border-t border-line py-3">
                  Purchase invoice <span className="font-mono text-[15px]">{top[0].record}</span> from {top[0].party}. Tax of {rupees(top[0].impact_paise)} claimed as credit.
                </dd>
                <dt className="border-t border-line py-3 text-ink-2">In GSTR-2B</dt>
                <dd className="border-t border-line py-3">No line from that supplier with that invoice number, this month or the next.</dd>
                <dt className="border-y border-line py-3 text-ink-2">So</dt>
                <dd className="border-y border-line py-3 font-semibold text-orange-deep">{rupees(top[0].impact_paise)} of credit is at risk until the supplier reports it.</dd>
              </dl>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="scroll-mt-10 bg-cream py-24">
        <div className={`grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-start gap-14 ${WIDE}`}>
          <div className="sticky top-10">
            <h2 className={H2}>Seven stages, one month.</h2>
            <p className={LEAD}>
              This is the Run for September 2025, replayed. Each stage reports what it found, and the lines going by are real records from that month: an invoice number a supplier wrote
              its own way, one payment settling two invoices, a round trip of money.
            </p>
            <p className="mt-8 max-w-[26ch] font-display text-[28px] font-bold leading-[1.2]">Code decides every number. The language model only words the explanation and the draft.</p>
          </div>
          <RunDemo stages={data.run.stages as StageEvent[]} items={data.run.items as FeedItem[]} />
        </div>
      </section>

      <section id="fix" className="scroll-mt-10 py-28">
        <div className={`grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-start gap-14 ${WIDE}`}>
          <div className="sticky top-10">
            <h2 className={H2}>Evidence, then a fix you approve.</h2>
            <p className={LEAD}>
              Every Finding shows the record next to what it should be, the rule that applies and the reason in plain words. Then a draft: a supplier email, a credit note or a ledger
              entry. Nothing leaves without your approval.
            </p>
            <p className="mt-8 max-w-[24ch] font-display text-[28px] font-bold leading-[1.2] text-orange-deep">This one is real. Press Approve draft and watch the month&apos;s numbers move.</p>
          </div>
          <FindingDemo finding={data.finding as DemoFinding} excessPaise={summary.excess_tax_paise} netPayablePaise={summary.net_payable_paise} />
        </div>
      </section>

      {data.ring.story && (
        <section id="ring" className="scroll-mt-10 bg-cream py-24">
          <div className={WIDE}>
            <h2 className={`max-w-[16ch] ${H2}`}>A supplier and a customer with one owner.</h2>
            <p className={LEAD}>
              LedgerLens looks across everyone the company trades with. Here two registrations carry the same PAN, and money went out and came back with no invoice. It reports the link and
              what it puts at stake; a person decides what it means.
            </p>
            <div className="mt-12 grid gap-14">
              <RingStory story={data.ring.story as Story} period={data.period} creditAtRisk={data.ring.credit_paise} />
            </div>
          </div>
        </section>
      )}

      <section id="proof" className="scroll-mt-10 py-28">
        <div className={`grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-start gap-14 ${WIDE}`}>
          <div className="sticky top-10">
            <h2 className={H2}>Measured, not claimed.</h2>
            <p className={LEAD}>
              The demo data has mistakes planted on purpose and a list of every one, so the catch rate and the false alarms can be counted. Switch between the two unseen months and the
              whole year: the misses are shown either way.
            </p>
          </div>
          <ProofDemo proof={data.proof as DemoProof} />
        </div>
      </section>

      <section id="data" className="scroll-mt-10 bg-orange-soft py-24">
        <div className={WIDE}>
          <h2 className={H2}>About the data</h2>
          <div className="mt-10 grid grid-cols-3 gap-x-12 text-[18px] leading-relaxed">
            {[
              ["The company is made up.", "One year of books, April 2025 to March 2026, for a trader in Delhi. No real business or person is in it."],
              ["The mistakes are planted.", "Typos, duplicates, wrong rates, missing filings and a supplier ring, with a list of every one. That list is how accuracy is measured."],
              ["Real books will differ.", "Synthetic data is cleaner than the real thing. The numbers show the method works, not what it will score on your books."],
            ].map(([head, body]) => (
              <div key={head}>
                <p className="font-display text-[26px] font-bold leading-tight">{head}</p>
                <p className="mt-2 text-ink-2">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-orange-deep py-24 text-white">
        <div className={WIDE}>
          <h2 className="max-w-[16ch] font-display text-[76px] font-extrabold leading-[0.96] tracking-[-0.03em]">Reconcile September 2025 now.</h2>
          <div className="mt-9 [&_.btn-primary]:border-ink [&_.btn-primary]:bg-ink">
            <StartActions onDark />
          </div>
        </div>
      </section>

      <footer className="bg-side">
        <p className={`py-6 text-[14px] text-cream/60 ${WIDE}`}>LedgerLens. Built for Fintechstico V7.0, NSUT Consilium&apos;26, problem statement 2.</p>
      </footer>
    </div>
  );
}
