Based on the TODO files, here's the recommended execution order — each level unblocks the next:

Execution Order
----------------------------------------------------------
Wave 1 — Core Tax Engine (P1, no dependencies) - done
2.7 — National insurance dual-rate calculation (tax_engine.py) - done
2.2 — Tax bracket breakdown in response (tax_engine.py) - done
4.3 — Partial expense recognition rates (annual_report_detail model + financial_service.py) - done
Wave 2 — Fields & Data Model (P2, depends on Wave 1) - done
wave complete
----------------------------------------------------------
5.1 / 5.2 — Recognition rate on deduction lines (resolved by 4.3) - done
5.3 — supporting_document_ref + recognition_rate on expense create/update - done
5.4 — Per-source credit point breakdown (pension/life insurance/tuition) - done
4.5 — net_profit field in tax calculation response - done
2.11 — total_liability aggregating NI + VAT + income tax (needs 2.7) - done
6.4 — tax_year field on PermanentDocument - done
6.7 — Document-deduction foreign key link (needs 6.4 + 5.3) - done
3.9 — notes field on AdvancePayment - done
wave complete
----------------------------------------------------------
Wave 3 — Advance Payments Analytics (P2)
3.4 — Delta (expected − paid) in response  - done
3.11 — Status filter on list endpoint  - done
3.10 — Delete advance payment endpoint  - done
3.6 / 3.5 — collection_rate + annual KPI cards - done
3.12 — Monthly chart data endpoint - done
wave complete
----------------------------------------------------------
Wave 4 — Report Workflows (P2)
7.6 — AMENDED status + amend endpoint - done
1.3 — Auto-compute profit/balance at report creation (needs financial_service stable) - done
7.1 — Filing timeline endpoint - done
[INTEGRATION — SKIP] 1.9 / 10.4 — ITA submission integration (stub → real API)
wave complete execpt 1.9 / 10.4 
----------------------------------------------------------
Wave 5 — Notifications (P2) — done
8.1 — severity field on Notification model - done 
8.3 — is_read field + bulk mark-as-read (needs 8.1) - done
8.6 — Notification center endpoints (needs 8.3) - done
8.4 — Bulk send + WhatsApp channel - done
8.2 — available_actions on deadline/report responses - done
wave complete
----------------------------------------------------------
Wave 6 — Analytics & Export (P3, depends on Waves 1–3)
4.6 — gross_margin_pct
9.3 — Multi-year comparison endpoint
9.2 — YoY change % (needs 9.3)
9.4 — Effective rate trend (part of 9.3)
4.8 — Multi-year chart (resolved by 9.3)
9.1 — Dashboard tax KPI cards
9.5 / 9.6 / 9.7 — Dashboard margin, collection rate, total liability
----------------------------------------------------------
Wave 7 — Export & UX (P3)
10.1 — Annual report PDF export
10.2 — Annual report Excel export
10.5 — Submission certificate PDF
10.6 — Multi-year comparison export (needs 9.3)
5.6 — Savings opportunities engine
5.7 / 5.8 — Pension top-up + training fund (part of 5.6)
6.3 — Additional document categories
3.2 — Turnover-based advance suggestion
3.3 — FUTURE payment status
3.13 — Bulk reminder send
2.8 — Live calculation SSE endpoint
----------------------------------------------------------