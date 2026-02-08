# Binder & Billing CRM
## Notifications Engine Specification

---

## 1. Purpose
Specify notification triggers, delivery channels, and logging behavior.

---

## 2. Supported Channels
1. WhatsApp
2. SMS
3. Email

---

## 3. Trigger Events
1. Binder received
2. Binder ready for pickup
3. Binder overdue
4. Payment reminder

---

## 4. Message Template Tokens
1. `client_name`
2. `binder_number`
3. `days_in_office`
4. `amount_due`
5. `due_date`

---

## 5. Delivery Rules
1. Respect global enable/disable flag.
2. Respect per-client opt-out when implemented.
3. Retry transient failures up to 3 attempts.
4. Mark permanent failures without blocking business action.

---

## 6. Logging and Audit
1. Every send attempt writes one `notifications` row.
2. Store channel, type, sent time, and content snapshot.
3. Store delivery provider response code in app logs.

---

## 7. Idempotency
1. Prevent duplicate sends for same event and channel within configurable window.
2. Use deduplication key:
- `event_type + entity_id + channel + date_bucket`

---

## 8. Future Enhancements
1. Delivery status callbacks.
2. Per-client preferred channel priority.
3. Localization support for message templates.

---

*End of Notifications Engine Specification*
