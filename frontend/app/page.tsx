"use client";

import Image from "next/image";
import { StartActions } from "@/components/StartActions";
import { DEMO_MONTH, DEMO_STAGES } from "@/lib/demo-month";
import { rupees } from "@/lib/format";

const WIDE = "mx-auto max-w-[1280px] px-10";
const H2 = "font-display text-[64px] font-extrabold leading-[0.98] tracking-[-0.025em]";

type BlockProps = { title: string; text: string; fact: string; src: string; alt: string; flip?: boolean; dark?: boolean; crop?: "top" | "bottom" };

function Block({ title, text, fact, src, alt, flip = false, dark = false, crop }: BlockProps) {
  return (
    <div className={`grid grid-cols-12 items-center gap-x-12 ${WIDE}`}>
      <div className={`col-span-5 ${flip ? "order-2" : ""}`}>
        <h3 className="font-display text-[44px] font-extrabold leading-[1.02] tracking-[-0.02em]">{title}</h3>
        <p className={`mt-4 text-[18px] leading-relaxed ${dark ? "text-cream/75" : "text-ink-2"}`}>{text}</p>
        <p className={`mt-6 font-display text-[22px] font-bold leading-snug ${dark ? "text-orange" : "text-orange-deep"}`}>{fact}</p>
      </div>
      <div className="col-span-7">
        {/* A cropped screen keeps its own proportions; the frame cuts it at the top or the bottom. */}
        <div className={`relative overflow-hidden rounded-[14px] bg-paper shadow-float ${crop ? "h-[480px]" : ""}`}>
          <Image
            src={src}
            alt={alt}
            width={crop ? 960 : 2034}
            height={1350}
            unoptimized
            className={crop ? `absolute left-0 h-auto w-full ${crop === "bottom" ? "bottom-0" : "top-0"}` : "h-auto w-full"}
          />
        </div>
      </div>
    </div>
  );
}

export default function StartPage() {
  return (
    <div className="min-h-screen bg-paper text-[16px]">
      <section className="bg-side text-cream">
        <header className={`flex items-center justify-between py-6 ${WIDE}`}>
          <span className="font-display text-[24px] font-extrabold">LedgerLens</span>
          <nav aria-label="Page" className="flex items-center gap-8 text-[15px] text-cream/75">
            <a href="#problem" className="hover:text-cream">The problem</a>
            <a href="#how" className="hover:text-cream">How it works</a>
            <a href="#features" className="hover:text-cream">What you get</a>
            <a href="#data" className="hover:text-cream">The data</a>
          </nav>
        </header>
        <div className={`pb-56 pt-16 ${WIDE}`}>
          <h1 className="max-w-[15ch] font-display text-[92px] font-extrabold leading-[0.94] tracking-[-0.03em]">
            Your GST records disagree. <span className="text-orange">See what it costs.</span>
          </h1>
          <p className="mt-7 max-w-[52ch] text-[20px] leading-relaxed text-cream/80">
            LedgerLens reconciles a month of books, prices every mismatch in rupees, shows the evidence and drafts the fix for you to approve.
          </p>
          <div className="mt-9">
            <StartActions onDark withOverlay />
          </div>
          <p className="mt-4 text-[15px] text-cream/60">Demo company: {DEMO_MONTH.company}, Delhi. September 2025, the month GST rates changed.</p>
        </div>
      </section>

      <div className={`-mt-44 ${WIDE}`}>
        <div className="overflow-hidden rounded-[16px] shadow-float">
          <Image
            src="/landing/dashboard.png"
            alt="The dashboard for September 2025: credit at risk, credit found, net payable and the Findings to fix first"
            width={2034}
            height={1350}
            unoptimized
            preload
            className="h-auto w-full"
          />
        </div>
      </div>

      <section id="problem" className="scroll-mt-10 py-28">
        <div className={WIDE}>
          <h2 className={`max-w-[18ch] ${H2}`}>Four records describe one purchase. They rarely agree.</h2>
          <div className="mt-12 grid grid-cols-4 gap-x-10">
            {[
              [DEMO_MONTH.invoices.toLocaleString("en-IN"), "invoices", "What was bought and sold, and the tax on each."],
              [DEMO_MONTH.ledgerEntries.toLocaleString("en-IN"), "ledger entries", "What the accountant entered in the books."],
              [DEMO_MONTH.bankLines.toLocaleString("en-IN"), "bank lines", "What was actually paid and received."],
              ["GSTR-2B", "supplier filings", "What your suppliers reported to the GST portal."],
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
              <span className="text-orange-deep">{rupees(DEMO_MONTH.atRiskPaise)}</span> of credit at risk.
            </p>
            <div>
              <p className="text-[16px] font-semibold">One example from that month</p>
              <dl className="mt-3 grid grid-cols-[120px_1fr] gap-x-6 text-[17px] leading-relaxed">
                <dt className="border-t border-line py-3 text-ink-2">In the books</dt>
                <dd className="border-t border-line py-3">
                  Purchase invoice <span className="font-mono text-[15px]">VEN041-0020</span> from Titan Logistics Ltd, 12 Sep 2025. IGST of Rs 58,480 claimed as credit.
                </dd>
                <dt className="border-t border-line py-3 text-ink-2">In GSTR-2B</dt>
                <dd className="border-t border-line py-3">No line from that supplier with that invoice number, this month or the next.</dd>
                <dt className="border-y border-line py-3 text-ink-2">So</dt>
                <dd className="border-y border-line py-3 font-semibold text-orange-deep">Rs 58,480 of credit is at risk until the supplier reports it.</dd>
              </dl>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="scroll-mt-10 bg-cream py-24">
        <div className={WIDE}>
          <h2 className={H2}>Seven stages, one month.</h2>
          <p className="mt-4 max-w-[58ch] text-[18px] text-ink-2">Each stage reports what it found. These are the results for September 2025.</p>
          <ol className="mt-12 grid grid-cols-7 gap-x-5">
            {DEMO_STAGES.map((stage, i) => (
              <li key={stage.label} className="border-t-2 border-ink pt-3">
                <p className="font-display text-[56px] font-extrabold leading-none text-orange-deep">{i + 1}</p>
                <p className="mt-2 text-[17px] font-bold leading-tight">{stage.label}</p>
                <p className="mt-2 text-[14px] leading-snug text-ink-2">{stage.found}</p>
              </li>
            ))}
          </ol>
          <p className="mt-12 max-w-[40ch] font-display text-[28px] font-bold leading-[1.2]">
            Code decides every number. The language model only words the explanation and the draft.
          </p>
        </div>
      </section>

      <section id="features" className="grid scroll-mt-10 gap-28 py-28">
        <Block
          title="Evidence for every Finding"
          text="The record and what it should be, side by side, with the rule that applies and the reason in plain words."
          fact="Charged 28 percent three days after the rate became 18 percent: Rs 21,436 of excess tax."
          src="/landing/finding.png"
          alt="A Finding: the invoice rate next to the correct rate, the rule and the reason it was flagged"
          crop="top"
        />
        <Block
          flip
          title="A fix you approve"
          text="A draft supplier email, credit note or ledger entry, worded from the facts of the Finding. Nothing leaves without your approval."
          fact="Approve it and the headline numbers move."
          src="/landing/finding-draft.png"
          alt="A drafted note to the customer about the credit note, with the approve, edit and dismiss buttons"
          crop="bottom"
        />
      </section>

      <section className="bg-side py-28 text-cream">
        <Block
          dark
          title="Supplier rings"
          text="Suppliers and Customers that share one owner, and money that goes out and comes back."
          fact="One PAN behind a supplier and a customer. Rs 5,00,000 out on 30 Sep, back on 2 Oct."
          src="/landing/ring.png"
          alt="The network view with the linked supplier and customer marked"
        />
      </section>

      <section className="py-28">
        <Block
          flip
          title="Measured, not claimed"
          text="The demo data has mistakes planted on purpose and a list of every one, so catch rate and false alarms can be counted on months the matchers never trained on."
          fact="February and March 2026: 287 of 288 planted mistakes caught, 8 false alarms, every one listed."
          src="/landing/proof.png"
          alt="Catch rate and false alarms for each kind of Finding"
        />
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
