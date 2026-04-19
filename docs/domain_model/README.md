# Domain Model Decisions

This directory contains the current domain-model review and the derived decision artifacts.

## Files

- `DOMAIN_MODEL_REVIEW_SUMMARY.md`
  - current-state findings plus agreed target state for Layers 1-3
- `domain_decision_doc.docx`
  - Word-format decision document derived from the review
- `generate_ddd.js`
  - generator script for the Word decision document

## Source of Truth

Until implementation starts, the markdown review file is the working source of truth:

- `DOMAIN_MODEL_REVIEW_SUMMARY.md`

The Word document is a presentation/export artifact and should be regenerated or updated from the markdown decisions, not edited as the primary source.

## Working Rule

When domain decisions change:

1. update `DOMAIN_MODEL_REVIEW_SUMMARY.md`
2. update `generate_ddd.js` if the decision-doc structure changed
3. regenerate or refresh `domain_decision_doc.docx`
