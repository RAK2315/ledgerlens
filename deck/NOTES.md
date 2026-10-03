# LedgerLens ideathon deck

Source of truth is index.html. Build steps:

- python render.py writes out/LedgerLens_Fintechstico.pdf (vector, from Chrome) and per-slide PNGs.
- cd tools, then node html2pptx.js writes out/LedgerLens_Fintechstico.pptx (fully editable: native text boxes and shapes; icons and the small drawings are PNGs) and refreshes images/. Run npm install in tools first on a new machine.
- python tools/extract_template.py rebuilds tools/template.json from ~/Downloads/fintechstico_submission_format.pdf: the organiser's logos, headings, divider lines, waves and sparkles as native objects. Run it before node html2pptx.js if the template changes.
- tools/ppt_export.ps1 opens the PPTX in PowerPoint and exports PNGs and a PDF to out/ppt_check for visual checks.
- Speaker notes live in tools/notes.json. Slide text is also written out in LedgerLens_deck_content.md.

Fonts: the PPTX uses Inter, League Spartan and JetBrains Mono. They are in fonts/ and installed for this Windows user. On another machine, install the TTFs in fonts/ before opening the PPTX, or PowerPoint will substitute fonts and text will shift.

Format follows fintechstico_submission_format.pdf: 7 pages in the organiser's order (cover, problem statement, team, solution, architecture, technology used, feature/USP). The template page images in bg/ are the slide backgrounds.

## Open items before submitting

- Slide 3: team name and member names, colleges, roles are placeholders.
- Mockup numbers on slides 4 and 7 are illustrative product screens, not measured results. No accuracy figures are claimed anywhere.

## Sources for every fact on the slides

- 1.67 crore active GST taxpayers as of 30 Jun 2026: GSTN nine-year statistics, reported at https://a2ztaxcorp.net/nine-years-of-gst-taxpayer-base-crosses-1-67-crore-as-indias-digital-indirect-tax-ecosystem-scales-new-milestones-report-highlights-expansion-of-taxpayer-base-192-27-crore-returns-filed-an/ (accessed 2026-10-03)
- 18,876 ITC fraud cases, 17,818 fake firms, Rs 35,132 crore, Apr to Oct FY 2024-25: CBIC data via PIB, summarised in search results; related PIB releases https://www.pib.gov.in/PressReleasePage.aspx?PRID=1968923 and https://www.deccanherald.com/business/fake-itc-claims-detection-by-central-gst-officers-up-51-at-rs-36374-crore-in-fy24-3126661 (accessed 2026-10-03). Open the primary PIB release before quoting on stage.
- IMS accept, reject, pending and the end of auto ITC in GSTR-3B from Oct 2025; GSTR-3B liability locked to GSTR-1: https://taxguru.in/goods-and-service-tax/gst-ims-kills-auto-itc-gstr-3b-new-compliance-rules.html and https://tutorial.gst.gov.in/downloads/news/revised_advisory_on_ims.pdf (accessed 2026-10-03)
- GST 2.0 rate rationalisation effective 22 Sep 2025, slabs 5, 18 and 40 percent, cement 28 to 18 percent: https://cleartax.in/s/next-generation-gst-reforms and https://www.ey.com/en_in/technical/alerts-hub/2025/09/gst-council-announces-major-rate-rationalization-and-trade-facilitation-measures (accessed 2026-10-03)
- Rule 37 (180-day payment), Section 16(2) conditions, Section 16(4) time limit of 30 Nov after the financial year, Section 17(5) blocked credits: CGST Act and Rules. Verify exact clause text against cbic-gst.gov.in before the build phase.
- PAN occupies characters 3 to 12 of a GSTIN: standard GSTIN structure, verify and unit test in the build phase.

## Dataset decisions (2026-10-03)

- Base dataset: ~/Downloads/tax_recon_dataset.xlsx. Sheets: invoices (5,197), bank_transactions (4,690), accounting_ledger (9,948), tax_rates (effective-dated, includes the 22 Sep 2025 cutover), party_master (120, all GSTIN check digits valid), tax_filings (monthly simplified GSTR-3B), answer_key (true liability per month), labels (2,149 rows: 781 real issues across 30 types, 1,368 benign traps across 6 types), links (true invoice, booking, bank and receipt links). Copy it into the repo at build time.
- Gaps to fill at build time: no GSTR-2B sheet (generate from purchase invoices with supplier filing behaviour), no Rule 37 180-day cases, no Section 17(5) blocked credits, no cancelled GSTINs, no PAN-linked supplier rings.
- github.com/AnujSureshkumar/synthetic-finance-data (MIT): borrow the CBIC-style GSTR-2B JSON shape and its five match classes; optional PDF invoice rendering.
- github.com/R3n0va/synthetic-accounting-data-generator: German VAT, not used.
- Deck numbers on slide 6 come from this file. If the dataset changes, update slide 6.
