# 04 Design system

The deck mockups are the target look: deck/index.html (sections 4 and 7) and deck/images/mockups/*.png. Light theme only.

## Tokens

Put these in frontend/app/globals.css as CSS variables and map them in the Tailwind theme. One source of truth; no raw hex in components.

| Token | Value | Role |
|---|---|---|
| --cream | #FFEFD8 | page background behind cards on the start screen |
| --cream-2 | #FFF7EC | soft card fill |
| --paper | #FFFFFF | app surfaces, cards, tables |
| --app-bg | #FBF8F5 | main content background inside the shell |
| --ink | #24110C | primary text, primary buttons |
| --ink-2 | #5B4339 | secondary text |
| --ink-3 | #8C7368 | captions, table headers |
| --line | rgba(36,17,12,.13) | borders |
| --line-2 | rgba(36,17,12,.07) | row dividers |
| --side | #1F1714 | sidebar |
| --orange | #F28C3A | accent, charts |
| --orange-deep | #D2601A | primary action button, ITC at risk number, links |
| --orange-soft | #FDDDBF | accent tint |
| --ok / --ok-soft | #2E9D6A / #DDF3E8 | matched, ITC found, approved |
| --bad / --bad-soft | #D64545 / #FBE1DF | Findings with money at risk, errors |
| --dup / --dup-soft | #C98A12 / #FBEFD2 | duplicates, review Band |
| --miss / --miss-soft | #6957D6 / #E6E2FB | missing, unmatched |

Status colours are for state only, never decoration. ITC at risk is orange-deep, ITC found is ok green, excess or short tax is bad red.

Typography: League Spartan 700 and 800 for headline numbers and page titles; Inter 400, 600, 700 for UI; JetBrains Mono 500 for invoice numbers, GSTINs, amounts in tables. Self-host the TTFs from deck/fonts in frontend/public/fonts before the event (offline demo). Sizes: page title 28px, section 18px, body 14px, table 13px, captions 12px, headline numbers 28 to 40px.

Spacing scale 4, 8, 12, 16, 24, 32. Radius: 12px cards, 9px buttons, 999px pills. Shadow only on floating panels and the drawer: 0 20px 40px -20px rgba(80,30,10,.35).

Copy: sentence case everywhere, no ALL-CAPS, no emoji. Money as Rs with Indian grouping (Rs 4,20,000), lakhs abbreviated as Rs 4.82 L only in headline tiles.

## Layout shell

- Left sidebar, 64px wide, var(--side), icon buttons (lucide-react) for Dashboard, Workbench, Ring view, Liability, Proof; V2 adds Suppliers and Anomalies. Active item has an orange tint.
- Top bar inside main: Company name and GSTIN (mono), period selector (YYYY-MM, defaults to 2025-09), Run status pill, Run reconciliation button (orange-deep).
- Main area: var(--app-bg), 24px padding, max content width 1440px.
- Finding detail opens as a right drawer (560px) over the workbench and dashboard; it also has its own route /findings/[id] for deep links.

## Component states

Every data view handles all six. Build shared EmptyState and ErrorState components first.

| State | Look |
|---|---|
| loading | skeleton blocks the size of the final content, no spinners over tables |
| empty | one line of text and the next action, for example "No Findings in this period" |
| error | bad-soft panel, the error message from the API, a Retry button |
| stale | a Run older than the data (rerun needed): dup-soft banner with Run again |
| partial | Run failed mid-way: banner naming the failed stage, results so far shown |
| offline | LLM unavailable: Drafts show "Written from a template" tag, no error |

## Accessibility

Text contrast at least 4.5:1 (ink on paper passes; never put ink-3 on cream for body text). Status always has a text label as well as colour. All actions reachable by keyboard; the drawer traps focus and closes on Escape. Charts have a text summary for screen readers.

## Screen inventory and visual checks

| Screen | Route | Features | Correct render (browser check) |
|---|---|---|---|
| Start | / | F17 | Load demo company button visible; after click, StageStepper shows 7 stages turning done in order, then redirects to /dashboard |
| Dashboard | /dashboard | F18 | six KPI tiles (matched, discrepant, duplicates, missing, ITC at risk, ITC found) with real numbers; donut; ITC at risk by cause bars sorted by rupees; top 5 Findings table with action links; matches deck mockup layout |
| Workbench | /workbench | F20 | table with filters (category, type, Band, status); clicking a row opens the drawer; a One-to-many match shows one payment against its invoices with a sum line |
| Finding detail | /findings/[id] and drawer | F19, F21 | pills (type, Rs at risk, how sure); side-by-side table with differing cells highlighted; Why this was flagged; What to do; Draft with Approve and send, Edit draft, Dismiss with note; after approve, a success toast and the dashboard numbers change |
| Ring view | /graph | F22 | dark canvas panel as in the deck; ring members red, clean suppliers green, Company orange; clicking a ring shows the explanation panel with members, reason and Rs at risk |
| Liability | /liability | F23 | three tax type columns (IGST, CGST, SGST) with output, eligible ITC, net; declared vs computed with gap; simplified set-off badge |
| Proof | /proof | F25 | bars of Catch rate per Finding type and a table with planted, caught, false alarms; caption says test split |
| Suppliers | /suppliers | V3 | ranked table with risk tier and Draft follow-up |
| Anomalies | /anomalies | V4 | list with rule and reason per row |

For every screen: zero console errors, works at 1440x900 and 1920x1080 (demo widths), loading and empty states seen at least once.
