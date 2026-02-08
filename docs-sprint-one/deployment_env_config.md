# Binder & Billing CRM
## Deployment and Environment Configuration

---

## 1. Purpose
Define deployment environments, required configuration, and release safeguards.

---

## 2. Environments
1. Local: developer machine.
2. Staging: pre-production validation.
3. Production: live environment.

---

## 3. Required Environment Variables
1. `APP_ENV`
2. `PORT`
3. `DATABASE_URL`
4. `JWT_SECRET`
5. `JWT_TTL_HOURS`
6. `CORS_ALLOWED_ORIGINS`
7. `LOG_LEVEL`
8. `INVOICE_PROVIDER_BASE_URL`
9. `INVOICE_PROVIDER_API_KEY`
10. `NOTIFICATIONS_ENABLED`
11. `WHATSAPP_API_KEY` (if enabled)
12. `SMS_API_KEY` (if enabled)
13. `EMAIL_API_KEY` (if enabled)

---

## 4. Secrets Policy
1. Secrets must never be committed to git.
2. Use a secret manager per environment.
3. Rotate production secrets periodically.
4. Audit access to secret manager.

---

## 5. Deployment Workflow
1. Build artifact from tagged commit.
2. Run migrations before app switch-over.
3. Run post-deploy smoke tests.
4. Enable rollback to previous artifact.

---

## 6. Observability
1. Structured logs with request ID and user ID.
2. Metrics:
- API latency
- 4xx/5xx rates
- job success/failure counts

3. Alerts:
- high error rate
- failed migrations
- notification provider failures

---

## 7. Backup and Recovery
1. Daily automated DB backup.
2. Point-in-time recovery enabled (recommended).
3. Quarterly restore drill in staging.

---

## 8. Release Checklist
1. Migrations verified in staging.
2. Critical flow smoke tests passed.
3. Config variables present and valid.
4. Dashboard and logging healthy after deploy.

---

*End of Deployment and Environment Configuration*
