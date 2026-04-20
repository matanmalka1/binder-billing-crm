# Client Migration Map

מפה מלאה של כל השימושים במודל `Client` (deprecated) לפני הסרתו.
**שלב זה קריאה בלבד — לא לשנות שום קוד.**

---

## 1. Imports של `Client` — קוד אפליקציה

| קובץ                                                        | שורה  | מה מיובא                             | שימוש                                     |
| ----------------------------------------------------------- | ----- | ------------------------------------ | ----------------------------------------- |
| `app/clients/repositories/client_repository.py`             | 8     | `Client, ClientStatus, IdNumberType` | כל פעולות ה-CRUD על Client                |
| `app/clients/services/client_query_service.py`              | 7     | `Client, ClientStatus`               | שאילתות רשימה, ספירה, stats               |
| `app/clients/services/client_service.py`                    | 7     | `Client`                             | Orchestrator — delegation בלבד            |
| `app/clients/services/client_creation_service.py`           | 11    | `Client`                             | יצירת Client + LegalEntity + ClientRecord |
| `app/clients/services/client_update_service.py`             | 12    | `ClientStatus`                       | עדכון status + cascade ל-ClientRecord     |
| `app/clients/services/client_lifecycle_service.py`          | —     | `Client`                             | soft delete + restore                     |
| `app/clients/services/client_excel_service.py`              | 8     | `Client`                             | ייבוא/ייצוא Excel                         |
| `app/clients/api/clients.py`                                | 7     | `ClientStatus`                       | endpoint-level filtering                  |
| `app/clients/schemas/client.py`                             | 8     | `IdNumberType`                       | schema definition                         |
| `app/notification/services/notification_send_service.py`    | 9, 12 | `Client`                             | JOIN לשליפת phone/email לשליחה            |
| `app/vat_reports/repositories/vat_compliance_repository.py` | 8     | `Client`                             | JOIN לאגרגציית ציות מע"מ                  |
| `app/timeline/services/timeline_client_aggregator.py`       | 1     | `Client`                             | שליפת client לאירועי timeline             |
| `app/binders/services/client_onboarding_service.py`         | 6     | `Client`                             | office_client_number sequencing           |
| `app/businesses/repositories/business_repository_read.py`   | 26    | `Client` (lazy import)               | JOIN Business → Client                    |
| `app/annual_reports/repositories/report_repository.py`      | 152   | `Client` (lazy import)               | JOIN לדוחות שנתיים                        |

---

## 2. `db.query(Client)` / `session.query(Client)` — כל הקריאות

| קובץ                                     | שורה    | קריאה                                                              | מטרה                          | מקבילה חדשה                                       |
| ---------------------------------------- | ------- | ------------------------------------------------------------------ | ----------------------------- | ------------------------------------------------- |
| `client_repository.py`                   | 67      | `query(Client).filter(Client.id == client_id, deleted_at IS NULL)` | `get_by_id`                   | `ClientRecordRepository.get_by_id()`              |
| `client_repository.py`                   | 75      | `query(Client).filter(Client.id == client_id)`                     | `get_by_id_including_deleted` | `ClientRecordRepository` + deleted flag           |
| `client_repository.py`                   | 83      | `query(Client).filter(Client.id_number == ...)`                    | `get_active_by_id_number`     | `LegalEntityRepository.get_by_id_number()`        |
| `client_repository.py`                   | 91      | `query(Client).filter(...isnot(None))`                             | `get_deleted_by_id_number`    | idem + deleted flag                               |
| `client_repository.py`                   | 99      | `query(Client).filter(Client.id == ...)`                           | `restore`                     | `ClientRecordRepository.restore()`                |
| `client_repository.py`                   | 111     | `query(Client).filter(Client.id == ...)`                           | `soft_delete`                 | `ClientRecordRepository.soft_delete()`            |
| `client_repository.py`                   | 126     | `query(Client).filter(deleted_at IS NULL)`                         | `_active_query` (base)        | `ClientRecordRepository._active_query()`          |
| `client_repository.py`                   | 188     | `query(Client).filter(Client.id.in_(...))`                         | `list_by_ids`                 | `ClientRecordRepository.list_by_ids()`            |
| `client_repository.py`                   | 196     | `query(Client).filter(deleted_at IS NULL)`                         | `list_all`                    | `ClientRecordRepository.list_all()`               |
| `notification_send_service.py`           | 56      | `.join(Client, Client.id == Business.client_id)`                   | notification delivery         | JOIN via `Business.legal_entity_id → LegalEntity` |
| `notification_send_service.py`           | 68–69   | `query(Client).filter(Client.id == client_record_id)`              | fetch phone/email             | `ClientRecord → LegalEntity → Person` (שלב 5+)    |
| `notification_send_service.py`           | 253–254 | idem                                                               | idem                          | idem                                              |
| `notification_send_service.py`           | 285–286 | `.join(Client, Client.id == ClientRecord.legal_entity_id)`         | join notification dispatch    | needs review post-migration                       |
| `vat_compliance_repository.py`           | 32      | `.join(Client, Client.id == ClientRecord.legal_entity_id)`         | VAT compliance aggregates     | replace with `JOIN LegalEntity`                   |
| `vat_compliance_repository.py`           | 71      | idem                                                               | overdue unfiled items         | idem                                              |
| `vat_compliance_repository.py`           | 94      | idem                                                               | stale pending items           | idem                                              |
| `businesses/business_repository_read.py` | 30      | `.join(Client, Client.id == Business.client_id)`                   | business list + client name   | replace with JOIN via `legal_entity_id`           |
| `timeline_client_aggregator.py`          | 28      | `query(Client).filter(Client.id == ClientRecord.legal_entity_id)`  | timeline client name          | `LegalEntityRepository.get_by_id()`               |
| `annual_reports/report_repository.py`    | 158     | `.join(Client, Client.id == ClientRecord.legal_entity_id)`         | annual report queries         | replace with `JOIN LegalEntity`                   |
| `tests/conftest.py`                      | 144     | `session.query(Client).filter(deleted_at IS NULL).all()`           | fixture: list active clients  | update fixture to use ClientRecord                |

---

## 3. `ClientResponse` Schema — שימושים

| קובץ                                   | שורה    | שימוש                                                      | מקבילה חדשה                     |
| -------------------------------------- | ------- | ---------------------------------------------------------- | ------------------------------- |
| `app/clients/schemas/client.py`        | 141     | הגדרת `ClientResponse(BaseModel)`                          | `ClientRecordResponse` (שלב 6+) |
| `app/clients/schemas/client.py`        | 179     | `ClientListResponse` → `items: list[ClientResponse]`       | idem                            |
| `app/clients/schemas/client.py`        | 186     | `CreateClientResponse` → `client: ClientResponse`          | idem                            |
| `app/clients/api/clients.py`           | 75      | `response_model=CreateClientResponse`                      | endpoint יצירה                  |
| `app/clients/api/clients.py`           | 117–119 | `ClientResponse.model_validate(client)`                    | build creation response         |
| `app/clients/api/clients.py`           | 147     | `[ClientResponse.model_validate(c) for c in items]`        | list response                   |
| `app/clients/api/clients.py`           | 158–163 | `response_model=ClientResponse`, `.model_validate(client)` | GET single                      |
| `app/clients/api/clients.py`           | 186–201 | idem                                                       | PATCH                           |
| `app/clients/api/clients.py`           | 223–230 | idem                                                       | POST /restore                   |
| `app/clients/api/client_enrichment.py` | 22–32   | `enrich_single/enrich_list(ClientResponse)`                | active_binder_number enrichment |

---

## 4. Foreign Keys לטבלת `clients`

| טבלה מקושרת  | עמודה       | הגדרה                                         | מצב                 |
| ------------ | ----------- | --------------------------------------------- | ------------------- |
| `businesses` | `client_id` | `ForeignKey("clients.id")` — עדיין קיים ב-ORM | **פעיל — טרם הוסר** |
| שאר הטבלאות  | `client_id` | הוסר ב-migration 0019                         | הוסר ✅             |

---

## 5. Relationships על Client

| Relationship          | סוג           | צד שני                              | שימוש       | מקבילה                                  |
| --------------------- | ------------- | ----------------------------------- | ----------- | --------------------------------------- |
| `entity_notes`        | 1:N, viewonly | `EntityNote` (entity_type='client') | הצמדת הערות | `EntityNote` על `ClientRecord` (שלב 5+) |
| `client` (ב-Business) | N:1, viewonly | `Business.client_id → Client`       | navigation  | `Business.legal_entity → LegalEntity`   |

---

## 6. שדות Client לפי קטגוריה

**זהות → LegalEntity:**

| שדה                       | סטטוס מיגרציה                                    |
| ------------------------- | ------------------------------------------------ |
| `id_number`               | ✅ קיים ב-LegalEntity                            |
| `id_number_type`          | ✅ קיים ב-LegalEntity                            |
| `entity_type`             | ✅ קיים ב-LegalEntity                            |
| `vat_reporting_frequency` | ✅ קיים ב-LegalEntity                            |
| `vat_exempt_ceiling`      | ✅ קיים ב-LegalEntity                            |
| `advance_rate`            | ✅ קיים ב-LegalEntity                            |
| `advance_rate_updated_at` | ✅ קיים ב-LegalEntity                            |
| `full_name`               | ✅ → `LegalEntity.official_name` (הושלם שלב 2–3) |

**CRM Record → ClientRecord:**

| שדה                    | סטטוס מיגרציה                                               |
| ---------------------- | ----------------------------------------------------------- |
| `status`               | ✅ קיים ב-ClientRecord (חלקי — לוודא FROZEN/CLOSED cascade) |
| `office_client_number` | ✅ קיים ב-ClientRecord                                      |
| `created_by`           | ✅ קיים ב-ClientRecord                                      |
| `created_at`           | ✅ קיים ב-ClientRecord                                      |
| `deleted_at`           | ✅ קיים ב-ClientRecord                                      |
| `deleted_by`           | לוודא                                                       |
| `restored_at`          | לוודא                                                       |
| `restored_by`          | לוודא                                                       |
| `notes`                | ❌ חסר ב-ClientRecord                                       |

**אישי / קשר → Person (שלב עתידי):**

| שדה                       | סטטוס מיגרציה                  |
| ------------------------- | ------------------------------ |
| `phone`                   | ❌ אין מקבילה — **בלוקר** לסרה |
| `email`                   | ❌ אין מקבילה — **בלוקר** לסרה |
| `address_street`          | ❌ אין מקבילה                  |
| `address_building_number` | ❌ אין מקבילה                  |
| `address_apartment`       | ❌ אין מקבילה                  |
| `address_city`            | ❌ אין מקבילה                  |
| `address_zip_code`        | ❌ אין מקבילה                  |
| `accountant_name`         | ❌ אין מקבילה                  |

---

## 7. כיסוי טסטים

| תחום                          | קבצים עם import Client | הערות                                          |
| ----------------------------- | ---------------------- | ---------------------------------------------- |
| `tests/clients/`              | ~11                    | ישנם כשלים pre-existing (`client_id` refactor) |
| `tests/conftest.py`           | 1                      | fixture מרכזי — שינוי ישפיע על הכל             |
| `tests/advance_payments/`     | 7                      | fixtures בלבד                                  |
| `tests/annual_reports/`       | 13                     | fixtures בלבד                                  |
| `tests/binders/`              | 8                      | fixtures בלבד                                  |
| `tests/businesses/`           | 4                      | fixtures + logic                               |
| `tests/vat_reports/`          | 4                      | fixtures + logic                               |
| `tests/notification/`         | עקיף                   | notification_send_service משתמש ב-Client       |
| `scripts/seed_fake_data_lib/` | 3                      | seed בלבד                                      |

**סה"כ: ~115 קבצי טסט.**
עדכון `conftest.py` לבדו יפתור את רוב המקרים.

---

## 8. סיכום תלויות לפי עדיפות הסרה

### קל — ניתן להסרה ב-Layer 2

- `vat_compliance_repository.py` — JOIN מיותר, ניתן להחליף ב-`JOIN LegalEntity`
- `annual_reports/report_repository.py` — idem
- `timeline_client_aggregator.py` — JOIN פשוט ל-`LegalEntity`

### בינוני — דורש schemas חדשים

- `clients.py` API + `ClientResponse` schema — המרה ל-`ClientRecordResponse`
- `businesses/business_repository_read.py` — JOIN דרך `legal_entity_id`

### בלוקר — דורש שדות חסרים

- `notification_send_service.py` — `Client.phone` / `Client.email` אין מקבילה עדיין
- `client_excel_service.py` — תלוי בכל שדות Client
- `Business.client_id` FK — עדיין קיים ב-ORM, צריך migration

---

## 9. קבצים קריטיים

| קובץ                                                        | תפקיד                     |
| ----------------------------------------------------------- | ------------------------- |
| `app/clients/models/client.py`                              | המודל המיועד לסרה         |
| `app/clients/models/legal_entity.py`                        | יעד עיקרי — זהות ישות     |
| `app/clients/models/client_record.py`                       | יעד עיקרי — רשומת CRM     |
| `app/clients/repositories/client_repository.py`             | 9 שיטות לפרסם             |
| `app/notification/services/notification_send_service.py`    | תלות בלוקינג              |
| `app/vat_reports/repositories/vat_compliance_repository.py` | JOINs לשנות               |
| `app/businesses/models/business.py`                         | `client_id` FK עדיין פעיל |
| `tests/conftest.py`                                         | fixture מרכזי             |
