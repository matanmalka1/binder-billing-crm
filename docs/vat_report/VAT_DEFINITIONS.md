# VAT_DEFINITIONS.md

## Purpose
A clean domain definitions file for Israeli VAT reporting.
This file is meant for system design and modeling.

Core rule:
**VAT reporting is always owned by the legal reporting entity (`client`), not by `business`.**

---

## 1. Legal Reporting Entities

### Taxable Entity (`חייב במס`)
**Definition:** A legal entity that is obligated to report or pay VAT under the law.  
**System meaning:** The top-level reporting owner in the system. Holds the VAT file and reporting obligations.  
**Ownership scope:** `Client`

### Dealer / Registered Dealer (`עוסק`)
**Definition:** A person, company, or partnership that sells goods or provides services in the course of business.  
**System meaning:** A VAT-reporting client type.  
**Ownership scope:** `Client`

### Authorized Dealer (`עוסק מורשה`)
**Definition:** A dealer that charges VAT, files periodic VAT reports, and may deduct input VAT subject to law.  
**System meaning:** A client that participates in the regular VAT reporting lifecycle.  
**Ownership scope:** `Client`

### Exempt Dealer (`עוסק פטור`)
**Definition:** A dealer below the legal turnover threshold, who does not charge VAT and does not deduct input VAT.  
**System meaning:** A client that does not file regular periodic VAT reports, but may still have annual VAT-related obligations.  
**Ownership scope:** `Client`

### Non-Profit Institution (`מלכ"ר`)
**Definition:** A non-profit body subject to special VAT-related rules, mainly salary tax rather than regular transaction VAT.  
**System meaning:** A special client type with a different reporting model.  
**Ownership scope:** `Client`

### Financial Institution (`מוסד כספי`)
**Definition:** A financial body subject to salary-and-profit tax rules rather than regular dealer VAT rules.  
**System meaning:** A special client type with a different reporting flow.  
**Ownership scope:** `Client`

### Partnership (`שותפות`)
**Definition:** A partnership that may be registered as one VAT-reporting entity, with partners jointly and severally liable.  
**System meaning:** A single reporting client when registered under one VAT number.  
**Ownership scope:** `Client`

---

## 2. Operational Context

### Business (`עסק`)
**Definition:** An activity, branch, or operational unit under a legal reporting entity.  
**System meaning:** UI and operational grouping only. Not the tax owner of VAT reports.  
**Ownership scope:** `Business`

---

## 3. Reporting Periods and Deadlines

### Reporting Period (`תקופת דיווח`)
**Definition:** The legal reporting unit for VAT filing, usually one month or two months.  
**System meaning:** Defines report boundaries and uniqueness.  
**Ownership scope:** `Tax Rule`

### Reporting Frequency (`תדירות דיווח`)
**Definition:** Monthly or bi-monthly reporting obligation, based on legal classification and turnover rules.  
**System meaning:** A client-level VAT rule used to generate periods and deadlines.  
**Ownership scope:** `Client`

### Filing Deadline (`מועד הגשה`)
**Definition:** The legal deadline for submitting a VAT report for a given reporting period.  
**System meaning:** Deadline used for tasks, reminders, overdue logic, and dashboard status.  
**Ownership scope:** `Tax Rule`

---

## 4. VAT Report Objects

### Periodic VAT Report (`דוח תקופתי`)
**Definition:** The report submitted for a reporting period summarizing taxable activity, input VAT, and payable/refundable VAT.  
**System meaning:** The root aggregate of the VAT reporting domain.  
**Ownership scope:** `Report`

### Zero Report (`דוח אפס`)
**Definition:** A periodic VAT report filed for a period with no reportable activity.  
**System meaning:** A report with zero activity. Should be modeled explicitly, not left ambiguous.  
**Ownership scope:** `Report`

### Corrected Report (`דוח מתקן`)
**Definition:** A correction to a report already submitted when a previously filed amount was wrong.  
**System meaning:** A correction workflow linked to an existing report or its filed version.  
**Ownership scope:** `Report`

### Supplemental Report (`דוח משלים`)
**Definition:** A filing used when data that should have been included in the original report was omitted.  
**System meaning:** Additional correction workflow tied to an existing reporting period.  
**Ownership scope:** `Report`

---

## 5. Source Documents

### Tax Invoice (`חשבונית מס`)
**Definition:** A VAT invoice issued by an authorized dealer and used as the main source for VAT reporting and input VAT deduction rules.  
**System meaning:** Primary source document for VAT transaction and input calculations.  
**Ownership scope:** `Document`

### Transaction Invoice (`חשבונית עסקה`)
**Definition:** A commercial invoice documenting a transaction, but not necessarily a valid document for input VAT deduction.  
**System meaning:** A business document that may support transaction tracking but is not a substitute for a tax invoice.  
**Ownership scope:** `Document`

### Receipt (`קבלה`)
**Definition:** A document confirming that payment was actually received.  
**System meaning:** Important for cash-basis timing rules.  
**Ownership scope:** `Document`

### Credit Note (`הודעת זיכוי`)
**Definition:** A correcting document used when a transaction is canceled or changed after invoice issuance.  
**System meaning:** Generates a negative adjustment against previously reported VAT amounts.  
**Ownership scope:** `Document`

### Import Entry (`רשימון יבוא`)
**Definition:** The official customs document proving import and VAT paid on imported goods.  
**System meaning:** Accepted source for deductible import input VAT where legally valid.  
**Ownership scope:** `Document`

### Allocation Number (`מספר הקצאה`)
**Definition:** A regulatory identifier required for certain invoices above a legal threshold as a condition for input VAT deduction.  
**System meaning:** Validation requirement on purchase-side documents above the relevant threshold.  
**Ownership scope:** `Document` + `Tax Rule`

---

## 6. Tax Amounts and Classifications

### Turnover (`מחזור עסקאות`)
**Definition:** The reportable value of transactions for the reporting period according to VAT rules.  
**System meaning:** A report-level aggregated amount.  
**Ownership scope:** `Report`

### Output VAT (`מס עסקאות`)
**Definition:** VAT charged by the reporting entity on taxable transactions.  
**System meaning:** The gross VAT liability generated from outgoing taxable activity.  
**Ownership scope:** `Report`

### Input VAT (`מס תשומות`)
**Definition:** VAT paid on business purchases or imports, deductible subject to legal conditions.  
**System meaning:** The deductible VAT component that reduces net VAT payable.  
**Ownership scope:** `Report`

### Capital Input VAT (`תשומות ציוד`)
**Definition:** Input VAT on capital or equipment-related acquisitions.  
**System meaning:** A distinct report field and classification that must not be merged into general inputs.  
**Ownership scope:** `Report`

### Other Input VAT (`תשומות אחרות`)
**Definition:** Input VAT on current or non-capital business expenses.  
**System meaning:** A distinct report field for non-capital deductible inputs.  
**Ownership scope:** `Report`

### VAT Payment (`תשלום מע"מ`)
**Definition:** The net amount payable to the tax authority for the reporting period.  
**System meaning:** Payment obligation generated after VAT netting.  
**Ownership scope:** `Payment`

### VAT Refund (`החזר מע"מ`)
**Definition:** The net amount refundable to the reporting entity when deductible input VAT exceeds output VAT.  
**System meaning:** Refund-side payment result of the report.  
**Ownership scope:** `Payment`

---

## 7. Tax Rules

### Cash Basis (`בסיס מזומן`)
**Definition:** A VAT timing rule where tax liability arises upon receipt of payment, subject to applicable law.  
**System meaning:** Document-to-period assignment logic based on actual payment timing.  
**Ownership scope:** `Tax Rule`

### Accrual / Invoice Timing Basis (`בסיס מצטבר`)
**Definition:** A VAT timing rule where tax liability is determined by the legal tax point and not necessarily by payment receipt.  
**System meaning:** Period assignment logic based on the legally relevant tax point.  
**Ownership scope:** `Tax Rule`

### Tax Point (`מועד החיוב במס`)
**Definition:** The legal moment when VAT liability is formed and the applicable VAT rate is determined.  
**System meaning:** The decisive time key for rate selection and report assignment.  
**Ownership scope:** `Tax Rule`

### Taxable Transaction (`עסקה חייבת`)
**Definition:** A transaction subject to regular VAT.  
**System meaning:** Produces output VAT.  
**Ownership scope:** `Tax Rule`

### Zero-Rated Transaction (`עסקה בשיעור אפס`)
**Definition:** A transaction taxed at 0%, while preserving input VAT deduction rights where legally allowed.  
**System meaning:** Produces turnover without output VAT while preserving deduction behavior.  
**Ownership scope:** `Tax Rule`

### Exempt Transaction (`עסקה פטורה`)
**Definition:** A transaction exempt from VAT and generally not eligible for related input VAT deduction.  
**System meaning:** Produces turnover classification without output VAT and with restricted deduction logic.  
**Ownership scope:** `Tax Rule`

---

## 8. Modeling Rules

1. **VAT report ownership is always `client_id`.**
2. **`business_id` may exist only as optional operational context.**
3. **One reporting entity per VAT registration number.**
4. **One VAT report per reporting entity per reporting period.**
5. **Zero report must be modeled explicitly.**
6. **Input VAT must be split between capital inputs and other inputs.**
7. **Correction workflows must stay linked to the original reporting period.**
8. **Allocation number rules must be enforced at document-validation level.**
9. **Tax point logic must drive VAT rate selection and period assignment.**
10. **Do not model legal reporting ownership on `business`.**

---

## 9. Common Confusion / Do Not Mix

### `Client` vs `Business`
- `Client` = legal reporting entity.
- `Business` = internal grouping, activity, or branch.
- VAT reports belong to `Client`, not to `Business`.

### `Tax Invoice` vs `Transaction Invoice`
- Tax invoice is relevant for VAT reporting and input deduction.
- Transaction invoice is not automatically enough for VAT deduction.

### `Zero-Rated` vs `Exempt`
- Zero-rated does not mean exempt.
- Zero-rated may preserve input VAT deduction rights.
- Exempt usually does not.

### `Corrected Report` vs `Supplemental Report`
- Both are post-submission correction flows.
- They should not be treated as free-floating unrelated reports.

### `Cash Basis` vs `Tax Point`
- Cash basis is one timing rule.
- Tax point is the legal event that ultimately controls VAT timing.
- They are related, not identical.
