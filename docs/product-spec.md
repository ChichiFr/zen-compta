# Zen Compta Product Spec

## Purpose

Zen Compta is an internal financial management tool for a restaurant. The first
version focuses on making invoices, VAT, monthly sales, and estimated cash flow
clear, reliable, and easy to verify.

The app is designed for two initial users: the restaurant owner and a family
member helping with management.

## MVP Goals

- Track supplier invoices accurately.
- Support manual invoice entry and AI-assisted document upload.
- Separate HT, TVA, and TTC everywhere.
- Support invoice lines with multiple VAT rates.
- Require human validation before invoices affect official totals.
- Track monthly sales totals for VAT calculations.
- Show a dashboard for invoice status, VAT, and estimated cash flow.
- Export clean CSV/Excel files for accounting review.

## Non-Goals For MVP

- Bank connection or Plaid integration.
- Bank reconciliation.
- Payroll and staffing.
- Multi-restaurant SaaS accounts.
- Full accounting ledger with debit/credit journal entries.
- Expert-comptable export formats such as FEC.
- Automatic invoice validation by AI.

## Users

### Owner

- Reviews invoices.
- Confirms totals and VAT.
- Checks dashboard status.
- Exports data for accounting.

### Family Manager

- Uploads or enters invoices.
- Corrects AI extraction results.
- Enters monthly sales totals.
- Prepares exports.

## Core Workflows

### Manual Invoice Entry

1. User creates a new invoice manually.
2. User enters supplier, date, invoice number when available, and one or more
   invoice lines.
3. Each line includes description, category, VAT rate, HT, TVA, and TTC.
4. Invoice starts as `draft`.
5. User reviews and validates the invoice.
6. Validated invoice is included in VAT totals, dashboard totals, and exports.

### AI-Assisted Invoice Upload

1. User uploads a PDF or image of an invoice.
2. The backend stores the document outside the database.
3. AI extracts supplier, date, invoice number, line items, VAT rates, HT, TVA,
   and TTC when possible.
4. The app creates a draft invoice from the extracted data.
5. Fields with low confidence are marked as `needs_review`.
6. User corrects or confirms the extracted data.
7. Validation remains blocked until required fields are complete and confirmed.

### Monthly Sales Entry

1. User selects a month.
2. User enters monthly sales totals: HT, TVA collected, and TTC.
3. The app uses sales TVA as collected VAT for the selected period.
4. Sales data appears in the dashboard VAT summary.

### Export

1. User selects a period.
2. User exports validated invoice data and VAT details.
3. Export formats: CSV first, Excel later if needed.
4. Draft invoices are excluded from official exports.

## Dashboard MVP

The dashboard answers: "Where are we this month for invoices, VAT, and estimated
cash flow?"

### KPI Cards

- Factures a verifier.
- Factures validees.
- TVA deductible.
- TVA collectee.
- TVA a payer estimee.
- Tresorerie estimee.

### VAT Summary

VAT payable is calculated as:

```text
TVA a payer = TVA collectee - TVA deductible
```

Only validated supplier invoices count toward deductible VAT.

### Estimated Cash Flow

Cash flow is an estimate until bank integration exists.

```text
Tresorerie estimee =
  solde initial de periode
  + ventes TTC
  - factures TTC validees
  - TVA a payer estimee
```

The dashboard must clearly label this as an estimate not connected to the bank.

### Action List

The dashboard should highlight operational tasks:

- Validate draft invoices.
- Review invoices with uncertain AI fields.
- Complete missing categories.
- Enter monthly sales.
- Export VAT/accounting data.

## Data Concepts

### Invoice

Represents a supplier invoice. An invoice has supplier details, dates, optional
invoice number, status, source, document metadata, and totals derived from its
lines.

### Invoice Line

Represents one accounting/VAT line on an invoice. Multi-rate VAT is handled at
this level.

Each line tracks:

- Description.
- Category.
- VAT rate.
- HT amount.
- VAT amount.
- TTC amount.

### Monthly Sales

Represents monthly sales totals used for VAT calculations.

Each record tracks:

- Month.
- Sales HT.
- VAT collected.
- Sales TTC.

### Document Import

Represents an uploaded invoice document and AI extraction status. The database
stores metadata and a file location, not the document content as base64.

## Invoice Statuses

- `draft`: editable and not included in official totals.
- `needs_review`: extracted or entered data requires user confirmation.
- `validated`: included in dashboard totals and exports.
- `archived`: kept for history but hidden from active workflows.

## Validation Rules

An invoice cannot be validated unless:

- Supplier is present.
- Invoice date is present.
- At least one invoice line exists.
- Every line has HT, TVA, TTC, and VAT rate.
- Line totals reconcile with invoice totals.
- AI uncertainty flags on required fields have been confirmed or corrected.

## Security And Privacy

- Real secrets must never be committed.
- Uploaded documents must not be committed.
- Uploaded documents must not be stored as base64 in PostgreSQL.
- AI extraction must not automatically validate invoices.
- Users must be authenticated before accessing invoice, sales, export, or
  dashboard data.

## Future Versions

Future versions may add:

- Bank import or Plaid integration.
- Bank reconciliation.
- Staffing and payroll.
- Cash flow forecasting.
- Multi-user roles.
- Multi-restaurant SaaS support.
- Full accounting ledger and expert-comptable exports.

