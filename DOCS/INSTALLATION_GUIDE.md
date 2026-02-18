# מדריך התקנה ואינטגרציה - תכונות חדשות

## 📦 קבצים שנוצרו

### Backend
1. **Models**
   - `app_models_reminder.py` - מודל תזכורות

2. **Services**
   - `app_services_reports.py` - שירות דוחות (Aging Report)
   - `app_services_export.py` - שירות ייצוא (Excel/PDF)
   - `app_services_reminder.py` - שירות תזכורות

3. **API**
   - `app_api_reports.py` - endpoints לדוחות וייצוא

4. **Schemas**
   - `app_schemas_reports.py` - סכימות לדוחות

5. **Documentation**
   - `FEATURES_DOCUMENTATION.md` - תיעוד מפורט

---

## 🚀 שלבי ההתקנה

### שלב 1: התקנת חבילות נדרשות

```bash
# עבור ייצוא Excel
pip install openpyxl

# עבור ייצוא PDF
pip install reportlab

# אופציונלי - עיבוד PDF
pip install PyPDF2
```

### שלב 2: העתקת הקבצים לפרויקט

```bash
# העתק קבצים למיקומים הנכונים
cp app_models_reminder.py ./app/models/reminder.py
cp app_services_reports.py ./app/services/reports_service.py
cp app_services_export.py ./app/services/export_service.py
cp app_services_reminder.py ./app/services/reminder_service.py
cp app_api_reports.py ./app/api/reports.py
cp app_schemas_reports.py ./app/schemas/reports.py
```

### שלב 3: עדכון ה-imports

#### app/models/__init__.py
הוסף:
```python
from app.models.reminder import Reminder, ReminderType, ReminderStatus

__all__ = [
    # ... existing imports
    "Reminder",
    "ReminderType",
    "ReminderStatus",
]
```

#### app/schemas/__init__.py
הוסף:
```python
from app.schemas.reports import (
    AgingReportResponse,
    AgingReportItem,
    ExportFormat,
    ReportExportResponse,
)

__all__ = [
    # ... existing imports
    "AgingReportResponse",
    "AgingReportItem",
    "ExportFormat",
    "ReportExportResponse",
]
```

#### app/api/__init__.py
הוסף:
```python
from app.api import (
    # ... existing imports
    reports,
)

__all__ = [
    # ... existing exports
    "reports",
]
```

#### app/services/__init__.py
הוסף:
```python
def __getattr__(name: str) -> Any:
    # ... existing imports ...
    
    if name == "AgingReportService":
        from app.reports.services.reports_service import AgingReportService
        return AgingReportService
    
    if name == "ExportService":
        from app.reports.services.export_service import ExportService
        return ExportService
    
    if name == "ReminderService":
        from app.reminders.services import ReminderService
        return ReminderService
```

### שלב 4: רישום ה-router ב-main.py

```python
# app/main.py

from app.api import (
    # ... existing imports
    reports,
)

# Register routes
app.include_router(reports.router, prefix="/api/v1")
```

### שלב 5: יצירת טבלת reminders בבסיס הנתונים

#### אופציה 1: Development (ORM יצור אוטומטית)
```bash
# מחק את ה-DB ותן לORM ליצור מחדש
rm binder_crm.db
APP_ENV=development python -m app.main
```

#### אופציה 2: Production (SQL ידני)
```sql
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    reminder_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    target_date DATE NOT NULL,
    days_before INTEGER NOT NULL,
    send_on DATE NOT NULL,
    binder_id INTEGER,
    charge_id INTEGER,
    tax_deadline_id INTEGER,
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    sent_at DATETIME,
    canceled_at DATETIME,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (binder_id) REFERENCES binders(id),
    FOREIGN KEY (charge_id) REFERENCES charges(id),
    FOREIGN KEY (tax_deadline_id) REFERENCES tax_deadlines(id)
);

CREATE INDEX idx_reminder_client ON reminders(client_id);
CREATE INDEX idx_reminder_binder ON reminders(binder_id);
CREATE INDEX idx_reminder_charge ON reminders(charge_id);
CREATE INDEX idx_reminder_tax_deadline ON reminders(tax_deadline_id);
CREATE INDEX idx_reminder_status_send_on ON reminders(status, send_on);
CREATE INDEX idx_reminder_target_date ON reminders(target_date);
CREATE INDEX idx_reminder_send_on ON reminders(send_on);
```

### שלב 6: יצירת תיקיית exports

```bash
mkdir -p /tmp/exports
chmod 755 /tmp/exports
```

---

## 🧪 בדיקת ההתקנה

### 1. בדיקת endpoint דוח חובות
```bash
curl -X GET "http://localhost:8000/api/v1/reports/aging" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

תוצאה צפויה:
```json
{
  "report_date": "2026-02-16",
  "total_outstanding": 0.0,
  "items": [],
  "summary": {
    "total_clients": 0,
    "total_current": 0.0,
    "total_30_days": 0.0,
    "total_60_days": 0.0,
    "total_90_plus": 0.0
  }
}
```

### 2. בדיקת ייצוא לExcel
```bash
curl -X GET "http://localhost:8000/api/v1/reports/aging/export?format=excel" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. בדיקת API documentation
```
http://localhost:8000/docs
```
חפש את הקבוצה "reports" - אמור להיות 2 endpoints:
- GET /api/v1/reports/aging
- GET /api/v1/reports/aging/export

---

## 🎯 דוגמאות שימוש

### יצירת תזכורת למועד מס

```python
from app.reminders.services import ReminderService

reminder_service = ReminderService(db)

# תזכורת 7 ימים לפני מועד מע"מ
reminder = reminder_service.create_tax_deadline_reminder(
    client_id=123,
    tax_deadline_id=456,
    target_date=date(2026, 3, 15),
    days_before=7,
)

print(f"תזכורת נוצרה: {reminder.id}")
print(f"תשלח בתאריך: {reminder.send_on}")
```

### הרצת Job יומי לתזכורות

```python
# הוסף ל-app/binders/services/daily_sla_job_service.py או צור job חדש

from app.reminders.services import ReminderService

def send_pending_reminders(db: Session):
    """שלח את כל התזכורות שמועד השליחה שלהן הגיע."""
    reminder_service = ReminderService(db)
    notification_service = NotificationService(db)
    
    pending = reminder_service.get_pending_reminders()
    
    for reminder in pending:
        try:
            # שלח הודעה
            client = reminder_service.client_repo.get_by_id(reminder.client_id)
            if client:
                notification_service.send_notification(
                    client_id=reminder.client_id,
                    trigger="reminder",
                    content=reminder.message,
                    binder_id=reminder.binder_id,
                )
                
                # סמן כנשלח
                reminder_service.mark_sent(reminder.id)
                
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder.id}: {e}")
```

---

## 📊 Frontend Integration

### רכיב לדוח חובות

```typescript
// components/AgingReport.tsx

import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

interface AgingReportData {
  report_date: string;
  total_outstanding: number;
  items: Array<{
    client_name: string;
    total_outstanding: number;
    current: number;
    days_30: number;
    days_60: number;
    days_90_plus: number;
  }>;
  summary: {
    total_clients: number;
    total_current: number;
    total_30_days: number;
    total_60_days: number;
    total_90_plus: number;
  };
}

export const AgingReport: React.FC = () => {
  const [data, setData] = useState<AgingReportData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const response = await api.get('/reports/aging');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching aging report:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportToExcel = async () => {
    try {
      const response = await api.get('/reports/aging/export?format=excel');
      window.location.href = response.data.download_url;
    } catch (error) {
      console.error('Error exporting to Excel:', error);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  if (loading) return <div>טוען...</div>;
  if (!data) return <div>אין נתונים</div>;

  return (
    <div className="aging-report">
      <div className="report-header">
        <h2>דוח חובות ללקוחות</h2>
        <div className="actions">
          <button onClick={exportToExcel}>
            ייצא לExcel
          </button>
          <button onClick={() => exportToPDF()}>
            ייצא לPDF
          </button>
        </div>
      </div>

      <div className="summary">
        <div className="stat">
          <h3>סה"כ חוב</h3>
          <p>₪{data.total_outstanding.toLocaleString()}</p>
        </div>
        <div className="stat">
          <h3>מס' לקוחות</h3>
          <p>{data.summary.total_clients}</p>
        </div>
      </div>

      <table className="aging-table">
        <thead>
          <tr>
            <th>שם לקוח</th>
            <th>סה"כ</th>
            <th>שוטף</th>
            <th>30-60</th>
            <th>60-90</th>
            <th>90+</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item, index) => (
            <tr key={index}>
              <td>{item.client_name}</td>
              <td>₪{item.total_outstanding.toLocaleString()}</td>
              <td>₪{item.current.toLocaleString()}</td>
              <td>₪{item.days_30.toLocaleString()}</td>
              <td>₪{item.days_60.toLocaleString()}</td>
              <td className="overdue">₪{item.days_90_plus.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

---

## 🔧 פתרון בעיות

### שגיאה: "openpyxl not installed"
```bash
pip install openpyxl
```

### שגיאה: "reportlab not installed"
```bash
pip install reportlab
```

### שגיאה: "Table reminders does not exist"
הרץ את ה-SQL migration או מחק את ה-DB ב-development

### הקובץ המיוצא לא נמצא
בדוק שהתיקייה `/tmp/exports` קיימת ויש לך הרשאות כתיבה

---

## ✅ Checklist סופי

- [ ] התקנת חבילות (openpyxl, reportlab)
- [ ] העתקת כל הקבצים
- [ ] עדכון __init__.py בכל המודולים
- [ ] רישום router ב-main.py
- [ ] יצירת טבלת reminders
- [ ] יצירת תיקיית exports
- [ ] בדיקת endpoints ב-/docs
- [ ] בדיקת דוח חובות
- [ ] בדיקת ייצוא לExcel
- [ ] בדיקת ייצוא לPDF
- [ ] אינטגרציה ב-Frontend (אופציונלי)

---

## 📞 תמיכה

לתיעוד מפורט: `FEATURES_DOCUMENTATION.md`

לשאלות: פתח issue בפרויקט
