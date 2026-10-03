"use client";

// Direction A, "working paper": a document on white, ruled lines, the month's statement as the hero.
import Image from "next/image";
import { StartActions } from "@/components/StartActions";
import { DEMO_CAUSES, DEMO_MONTH, DEMO_STAGES } from "@/lib/demo-month";
import { rupees } from "@/lib/format";

const amount = (paise: number) => rupees(paise).replace("Rs ", "");

function Section({ id, title, lead, children }: { id: string; title: string; lead?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="grid scroll-mt-20 grid-cols-12 gap-x-8 border-t border-ink py-16">
      <div className="col-span-3">
        <h2 className="font-display text-[28px] font-bold leading-[1.1] [text-wrap:balance]">{title}</h2>
        {lead && <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{lead}</p>}
      </div>
      <div className="col-span-9">{children}</div>
    </section>
  );
}

function StatementRow({ label, value, strong = false, colour = "" }: { label: string; value: string; strong?: boolean; colour?: string }) {
  return (
    <div className={`flex items-baseline justify-between gap-6 border-b border-line py-2.5 ${strong ? "font-semibold" : ""}`}>
      <span>{label}</span>
      <span className={`font-mono ${colour}`}>{value}</span>
    </div>
  );
}

function Screen({ src, alt, width, height, className = "" }: { src: string; alt: string; width: number; height: number; className?: string }) {
  return <Image src={src} alt={alt} width={width} height={height} unoptimized className={`w-full border border-line ${className}`} />;
}

function Feature({ title, text, fact, children }: { title: string; text: string; fact: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-12 gap-x-8 border-t border-line py-10 first:border-t-0 first:pt-0">
      <div className="col-span-4">
        <h3 className="font-display text-[22px] font-bold leading-tight">{title}</h3>
        <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{text}</p>
        <p className="mt-4 border-l border-ink pl-3 font-mono text-[13px] leading-relaxed">{fact}</p>
      </div>
      <div className="col-span-8">{children}</div>
    </div>
  );
}

export default function LandingA() {
  const largest = DEMO_CAUSES[0].paise;
  return (
    <div className="min-h-screen bg-paper text-[16px]">
      <header className="sticky top-0 z-10 border-b border-line bg-paper">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-8 py-4">
          <span className="font-display text-[22px] font-extrabold">LedgerLens</span>
          <nav aria-label="Page" className="flex items-center gap-8 text-[15px] text-ink-2">
            <a href="#problem" className="hover:text-ink">The problem</a>
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#features" className="hover:text-ink">What you get</a>
            <a href="#data" className="hover:text-ink">The data</a>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-8">
        <section className="grid grid-cols-12 items-start gap-x-8 py-20">
          <div className="col-span-7">
            <p className="text-[15px] text-ink-2">GST reconciliation for Indian businesses</p>
            <h1 className="mt-3 font-display text-[64px] font-extrabold leading-[0.98] tracking-[-0.025em] [text-wrap:balance]">
              Your GST records disagree. Here is what it costs, why, and the fix.
            </h1>
            <p className="mt-6 max-w-[56ch] text-[18px] leading-relaxed text-ink-2">
              LedgerLens reconciles a month of books end to end. Every mismatch gets a rupee value, the evidence behind it and a drafted fix that you approve in one click.
            </p>
            <div className="mt-8">
              <StartActions to="/dashboard/a" withOverlay />
            </div>
            <p className="mt-4 text-[14px] text-ink-2">Demo company: {DEMO_MONTH.company}, Delhi. September 2025, the month GST rates changed.</p>
          </div>

          <aside className="col-span-5 pl-6" aria-label="September 2025 as LedgerLens reads it">
            <div className="border-t-2 border-ink pt-3">
              <p className="flex items-baseline justify-between text-[14px] text-ink-2">
                <span>{DEMO_MONTH.company}, September 2025</span>
                <span className="font-mono">Rs</span>
              </p>
              <div className="mt-2 text-[16px]">
                <StatementRow label="Output tax on sales" value={amount(DEMO_MONTH.outputPaise)} />
                <StatementRow label="Credit claimed in the filed return" value={amount(DEMO_MONTH.claimedPaise)} />
                <StatementRow label="Less ITC at risk" value={`-${amount(DEMO_MONTH.atRiskPaise)}`} colour="text-orange-deep" strong />
                <StatementRow label="Eligible credit" value={amount(DEMO_MONTH.eligiblePaise)} />
                <div className="flex items-baseline justify-between gap-6 border-b-[3px] border-double border-ink py-3">
                  <span className="font-display text-[22px] font-bold">Net payable</span>
                  <span className="font-display text-[30px] font-extrabold">{amount(DEMO_MONTH.netPayablePaise)}</span>
                </div>
                <StatementRow label="ITC found, not yet claimed" value={amount(DEMO_MONTH.foundPaise)} colour="text-ok" strong />
              </div>
              <p className="mt-3 text-[14px] leading-relaxed text-ink-2">
                {DEMO_MONTH.findings} Findings sit behind these lines. Each one opens to the records, the rule and a drafted fix.
              </p>
            </div>
          </aside>
        </section>

        <Section id="problem" title="Four records, one purchase, and they rarely agree">
          <p className="max-w-[62ch] text-[18px] leading-relaxed">
            Every month a business has to make four records agree. Where they differ, input tax credit is lost or tax is overpaid, and today that is found late, by hand, in
            spreadsheets.
          </p>
          <dl className="mt-8 grid grid-cols-4 border-y border-line">
            {[
              ["Invoices", "What was bought and sold, and the tax on each."],
              ["Books (ledger)", "What the accountant entered."],
              ["Bank statement", "What was actually paid and received."],
              ["GSTR-2B", "What your suppliers reported to the GST portal."],
            ].map(([name, text]) => (
              <div key={name} className="border-l border-line py-5 pl-5 pr-4 first:border-l-0 first:pl-0">
                <dt className="font-display text-[20px] font-bold">{name}</dt>
                <dd className="mt-1 text-[15px] text-ink-2">{text}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-8 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-[15px]">
            <p className="col-span-2 mb-1 font-semibold">One example from the demo month</p>
            <span className="text-ink-2">In the books</span>
            <span>
              Purchase invoice <span className="font-mono">VEN041-0020</span> from Titan Logistics Ltd, 12 Sep 2025. IGST of Rs 58,480 claimed as credit.
            </span>
            <span className="text-ink-2">In GSTR-2B</span>
            <span>No line from that supplier with that invoice number, this month or the next.</span>
            <span className="text-ink-2">So</span>
            <span className="font-semibold text-orange-deep">Rs 58,480 of credit is at risk until the supplier reports it.</span>
          </div>
        </Section>

        <Section id="how" title="How a month is reconciled" lead="Seven stages, in order. The right-hand column is what each one found in September 2025.">
          <ol>
            {DEMO_STAGES.map((stage, i) => (
              <li key={stage.label} className="grid grid-cols-[32px_200px_1fr_300px] items-baseline gap-4 border-b border-line py-3.5 first:border-t">
                <span className="font-mono text-[14px] text-ink-3">{i + 1}</span>
                <span className="font-semibold">{stage.label}</span>
                <span className="text-[15px] text-ink-2">{stage.what}</span>
                <span className="text-right font-mono text-[13px]">{stage.found}</span>
              </li>
            ))}
          </ol>
          <p className="mt-6 max-w-[62ch] text-[15px] leading-relaxed text-ink-2">
            <span className="font-semibold text-ink">Code decides every number.</span> Tested rules and two trained matchers do the work. The language model only words the explanation and
            the draft.
          </p>
        </Section>

        <section id="features" className="scroll-mt-20 border-t border-ink py-16">
          <h2 className="mb-10 font-display text-[28px] font-bold leading-[1.1]">What you get</h2>

          <Feature
            title="Rupees first"
            text="Every mismatch is priced: credit at risk, credit you can still claim, tax charged too high or too low. The month opens on those three numbers and where they come from."
            fact="September 2025: Rs 2,81,615 at risk, Rs 3,098 found, Rs 34,96,926 payable."
          >
            <ol className="border-t border-line">
              {DEMO_CAUSES.slice(0, 6).map((cause) => (
                <li key={cause.label} className="grid grid-cols-[280px_1fr_100px] items-center gap-4 border-b border-line-2 py-2.5 text-[15px]">
                  <span>{cause.label}</span>
                  <span className="h-1.5 bg-line-2">
                    <span className="block h-full bg-orange-deep" style={{ width: `${(cause.paise / largest) * 100}%` }} />
                  </span>
                  <span className="text-right font-mono">{amount(cause.paise)}</span>
                </li>
              ))}
            </ol>
            <p className="mt-2 text-[13px] text-ink-2">ITC at risk by cause, September 2025, in rupees.</p>
          </Feature>

          <Feature
            title="Evidence for every Finding"
            text="The record and what it should be, side by side, with the rule that applies and the reason in plain words."
            fact="INV-2526-01431: charged 28 percent on 25 Sep 2025; the rate is 18 percent since 22 Sep 2025. Rs 21,436 excess tax."
          >
            <div className="h-[420px] overflow-hidden border border-line">
              <Image src="/landing/finding.png" alt="A Finding: the invoice rate next to the correct rate, the rule and the reason it was flagged" width={960} height={1350} unoptimized className="w-full" />
            </div>
          </Feature>

          <Feature
            title="A fix you approve"
            text="A draft supplier email, credit note or ledger entry, worded from the facts of the Finding. Nothing leaves without your approval, and the headline numbers move when you approve."
            fact="Drafts are worded by a language model from the facts above them. It does not decide any number."
          >
            <div className="flex h-[420px] items-end overflow-hidden border border-line">
              <Image src="/landing/finding.png" alt="A drafted note to the customer about the credit note, ready to approve" width={960} height={1350} unoptimized className="w-full" />
            </div>
          </Feature>

          <Feature
            title="Supplier rings"
            text="Suppliers and Customers that share one owner, and money that goes out and comes back."
            fact="Unity Infra Pvt Ltd and Unity Motors Ltd share one PAN. Rs 5,00,000 left on 30 Sep 2025 with no invoice and came back on 2 Oct 2025."
          >
            <Screen src="/landing/ring.png" alt="The network view with the linked supplier and customer marked" width={2034} height={1350} />
          </Feature>

          <Feature
            title="Measured, not claimed"
            text="The demo data has mistakes planted on purpose and a list of every one, so catch rate and false alarms can be counted on months the matchers never trained on."
            fact="February and March 2026: one planted outlier missed, 10 false alarms. The Proof page lists them."
          >
            <Screen src="/landing/proof.png" alt="Catch rate and false alarms for each kind of Finding" width={2034} height={1350} />
          </Feature>
        </section>

        <Section id="data" title="About the data" lead="What a judge should know before trusting any number on this page.">
          <div className="grid grid-cols-3 gap-x-8 text-[15px] leading-relaxed">
            <p>
              <span className="font-semibold">The company is made up.</span> One year of books, April 2025 to March 2026, for a trader in Delhi. No real business or person is in it.
            </p>
            <p>
              <span className="font-semibold">The mistakes are planted.</span> Typos, duplicates, wrong rates, missing filings and a supplier ring were put in on purpose, with a list of every
              one. That list is how accuracy is measured.
            </p>
            <p>
              <span className="font-semibold">Real books will differ.</span> Synthetic data is cleaner than the real thing. The numbers here show the method works, not what it will score
              on your books.
            </p>
          </div>
        </Section>

        <section className="border-t border-ink py-16">
          <h2 className="max-w-[20ch] font-display text-[44px] font-extrabold leading-[1.02] tracking-[-0.02em]">Reconcile September 2025 and see for yourself.</h2>
          <div className="mt-7">
            <StartActions to="/dashboard/a" />
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <p className="mx-auto max-w-[1180px] px-8 py-6 text-[14px] text-ink-2">LedgerLens. Built for Fintechstico V7.0, NSUT Consilium&apos;26, problem statement 2.</p>
      </footer>
    </div>
  );
}
