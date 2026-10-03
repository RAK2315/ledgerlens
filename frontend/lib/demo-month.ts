// September 2025 for the demo company, as the engine reports it. The landing page shows these before any data is loaded.
// If an engine change moves the dashboard numbers, update these with it.
export const DEMO_MONTH = {
  period: "2025-09",
  company: "Sharma Traders Pvt Ltd",
  invoices: 453,
  ledgerEntries: 898,
  bankLines: 453,
  findings: 129,
  outputPaise: 611248280,
  claimedPaise: 289717173,
  atRiskPaise: 28161527,
  eligiblePaise: 261555646,
  netPayablePaise: 349692634,
  foundPaise: 309778,
};

export const DEMO_STAGES = [
  { label: "Read the records", what: "Invoices, ledger, bank statement and GSTR-2B for the month.", found: "453 invoices, 898 ledger entries, 453 bank lines" },
  { label: "Clean them up", what: "Invoice numbers and names typed in different ways are brought to one form.", found: "Bank lines traced to their Parties" },
  { label: "Match", what: "Each invoice to its booking, its payment and the Supplier's filing.", found: "1,018 matched automatically, 30 one-to-many, 1 for review" },
  { label: "Check the tax", what: "Rate on the invoice date, tax type, arithmetic, duplicates, the 180-day rule.", found: "106 Findings" },
  { label: "Look for anomalies", what: "Unusual invoices, and Suppliers linked to Customers.", found: "23 Anomalies, each with a reason" },
  { label: "Work out the money", what: "ITC at risk, ITC found and Net payable.", found: "Rs 2,81,615 at risk, Rs 3,098 found" },
  { label: "Explain", what: "A reason, the evidence and a next step for every Finding.", found: "129 Findings explained" },
];

export const DEMO_CAUSES = [
  { label: "Supplier has not reported the invoice", paise: 13501228 },
  { label: "Supplier and Customer share an owner", paise: 5361689 },
  { label: "IGST and CGST plus SGST mixed up", paise: 4608689 },
  { label: "Invoice entered twice", paise: 1919727 },
  { label: "Supplier unpaid for over 180 days", paise: 1300104 },
  { label: "Supplier reported a different amount", paise: 824523 },
  { label: "GSTIN is not valid", paise: 553468 },
  { label: "Tax does not add up", paise: 92099 },
];
