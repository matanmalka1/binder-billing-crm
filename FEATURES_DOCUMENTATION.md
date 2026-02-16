# תיעוד תכונות חדשות - דוחות ותזכורות

## 📋 סקירה כללית

תיעוד זה מתאר את התכונות החדשות שנוספו למערכת:

1. **דוח חובות ללקוחות (Aging Report)** - דוח פיננסי מפורט של חובות לקוחות לפי גיל החוב
2. **ייצוא דוחות** - ייצוא לאקסל ו-PDF
3. **מערכת תזכורות** - תזכורות פרואקטיביות למועדי מס, תיקים לא מטופלים וחשבוניות לא משולמות
4. **תצוגת PDF** - צפייה במסמכי PDF בתוך המערכת

---

## 1. דוח חובות ללקוחות (Aging Report)

### מה זה?
דוח פיננסי המציג את כל החובות הפתוחים של לקוחות, מסווג לפי גיל החוב:
- **שוטף (0-30 ימים)** - חובות עדכניים
- **30-60 ימים** - חובות בני חודש עד חודשיים
- **60-90 ימים** - חובות בני 2-3 חודשים
- **90+ ימים** - חובות ישנים

### API Endpoints

#### GET /api/v1/reports/aging
קבלת דוח חובות.

**Authorization:** ADVISOR בלבד

**Query Parameters:**
- `as_of_date` (optional): תאריך הדוח. ברירת מחדל: היום

**Response Example:**
```json
{
  "report_date": "2026-02-16",
  "total_outstanding": 45000.00,
  "items": [
    {
      "client_id": 123,
      "client_name": "חברת דוגמה בע\"מ",
      "total_outstanding": 15000.00,
      "current": 5000.00,
      "days_30": 3000.00,
      "days_60": 2000.00,
      "days_90_plus": 5000.00,
      "oldest_invoice_date": "2025-10-15",
      "oldest_invoice_days": 124
    }
  ],
  "summary": {
    "total_clients": 15,
    "total_current": 12000.00,
    "total_30_days": 8000.00,
    "total_60_days": 10000.00,
    "total_90_plus": 15000.00
  }
}
```

---

## 2. ייצוא דוחות

### API Endpoint

#### GET /api/v1/reports/aging/export
ייצוא דוח חובות לפורמט אקסל או PDF.

**Authorization:** ADVISOR בלבד

**Query Parameters:**
- `format` (required): `excel` או `pdf`
- `as_of_date` (optional): תאריך הדוח

**Response Example:**
```json
{
  "download_url": "/exports/aging_report_20260216_143022.xlsx",
  "filename": "aging_report_20260216_143022.xlsx",
  "format": "excel",
  "generated_at": "2026-02-16T14:30:22"
}
```

### דוגמת שימוש - Frontend

```typescript
// Export to Excel
const exportToExcel = async () => {
  const response = await fetch(
    '/api/v1/reports/aging/export?format=excel',
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );
  
  const data = await response.json();
  
  // Download the file
  window.location.href = data.download_url;
};

// Export to PDF
const exportToPDF = async () => {
  const response = await fetch(
    '/api/v1/reports/aging/export?format=pdf',
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );
  
  const data = await response.json();
  window.location.href = data.download_url;
};
```

---

## 3. מערכת תזכורות

### מודל נתונים

```python
class ReminderType:
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"
    BINDER_IDLE = "binder_idle"
    UNPAID_CHARGE = "unpaid_charge"
    CUSTOM = "custom"

class ReminderStatus:
    PENDING = "pending"
    SENT = "sent"
    CANCELED = "canceled"
```

### שירות התזכורות

```python
from app.services_reminder import ReminderService

# יצירת תזכורת למועד מס (X ימים לפני)
reminder = reminder_service.create_tax_deadline_reminder(
    client_id=123,
    tax_deadline_id=456,
    target_date=date(2026, 3, 15),  # תאריך המועד
    days_before=7,  # לשלוח 7 ימים לפני
    message="תזכורת: מועד מס בעוד 7 ימים"
)

# תזכורת לתיק לא מטופל
reminder = reminder_service.create_idle_binder_reminder(
    client_id=123,
    binder_id=789,
    days_idle=14,  # התיק לא טופל 14 ימים
    message="תזכורת: תיק לא טופל 14 ימים"
)

# תזכורת לחשבונית לא משולמת
reminder = reminder_service.create_unpaid_charge_reminder(
    client_id=123,
    charge_id=321,
    days_unpaid=30,  # החשבונית לא שולמה 30 ימים
    message="תזכורת: חשבונית לא שולמה 30 ימים"
)
```

### תהליך אוטומטי יומי

מומלץ להריץ Job יומי שסורק ויוצר תזכורות אוטומטיות:

```python
def daily_reminder_job(db: Session):
    """
    Job יומי שיוצר תזכורות אוטומטיות.
    
    מריץ את הפעולות הבאות:
    1. בודק מועדי מס קרובים (7 ימים לפני)
    2. בודק תיקים שלא טופלו (14+ ימים)
    3. בודק חשבוניות לא משולמות (30+ ימים)
    """
    from app.services_reminder import ReminderService
    from app.services.tax_deadline_service import TaxDeadlineService
    from app.repositories.binder_repository import BinderRepository
    from app.repositories.charge_repository import ChargeRepository
    
    reminder_service = ReminderService(db)
    
    # 1. מועדי מס קרובים
    tax_service = TaxDeadlineService(db)
    upcoming_deadlines = tax_service.get_upcoming_deadlines(days_ahead=7)
    
    for deadline in upcoming_deadlines:
        try:
            reminder_service.create_tax_deadline_reminder(
                client_id=deadline.client_id,
                tax_deadline_id=deadline.id,
                target_date=deadline.due_date,
                days_before=7,
            )
        except Exception as e:
            logger.error(f"Failed to create deadline reminder: {e}")
    
    # 2. תיקים לא מטופלים
    binder_repo = BinderRepository(db)
    all_binders = binder_repo.list_active()
    
    for binder in all_binders:
        days_since_received = (date.today() - binder.received_at).days
        if days_since_received >= 14:
            try:
                reminder_service.create_idle_binder_reminder(
                    client_id=binder.client_id,
                    binder_id=binder.id,
                    days_idle=days_since_received,
                )
            except Exception as e:
                logger.error(f"Failed to create idle binder reminder: {e}")
    
    # 3. חשבוניות לא משולמות
    charge_repo = ChargeRepository(db)
    unpaid_charges = charge_repo.list_charges(
        status=ChargeStatus.ISSUED.value,
        page=1,
        page_size=1000,
    )
    
    for charge in unpaid_charges:
        if not charge.issued_at:
            continue
        days_unpaid = (date.today() - charge.issued_at.date()).days
        if days_unpaid >= 30:
            try:
                reminder_service.create_unpaid_charge_reminder(
                    client_id=charge.client_id,
                    charge_id=charge.id,
                    days_unpaid=days_unpaid,
                )
            except Exception as e:
                logger.error(f"Failed to create unpaid charge reminder: {e}")
```

---

## 4. תצוגת PDF במערכת

### Backend - הוספת endpoint להצגת PDF

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse

@router.get("/documents/{document_id}/view")
def view_pdf_document(
    document_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """
    הצגת PDF בתוך הדפדפן.
    """
    from app.services.permanent_document_service import PermanentDocumentService
    
    service = PermanentDocumentService(db)
    document = service.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # בדוק הרשאות
    if document.client_id != user.client_id and user.role != UserRole.ADVISOR:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # החזר את הקובץ
    file_path = f"./storage/{document.storage_key}"
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}  # הצג בדפדפן
    )
```

### Frontend - רכיב React להצגת PDF

```typescript
import React from 'react';

interface PDFViewerProps {
  documentId: number;
  title: string;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ documentId, title }) => {
  const viewUrl = `/api/v1/documents/${documentId}/view`;
  
  return (
    <div className="pdf-viewer-container">
      <div className="pdf-header">
        <h3>{title}</h3>
        <a 
          href={viewUrl} 
          download 
          className="btn-download"
        >
          הורד PDF
        </a>
      </div>
      
      <iframe
        src={viewUrl}
        className="pdf-iframe"
        title={title}
        style={{
          width: '100%',
          height: '800px',
          border: 'none',
          borderRadius: '8px'
        }}
      />
    </div>
  );
};
```

---

## 5. ייבוא/ייצוא Excel

### ייבוא נתונים מאקסל

```python
@router.post("/clients/import")
async def import_clients_from_excel(
    file: UploadFile,
    db: DBSession,
    user: CurrentUser,
):
    """
    ייבוא לקוחות מקובץ Excel.
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl not installed"
        )
    
    # קרא את הקובץ
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    
    created_count = 0
    errors = []
    
    # דלג על שורת כותרת
    for row in ws.iter_rows(min_row=2, values_only=True):
        try:
            full_name, id_number, client_type, phone, email = row
            
            # צור לקוח חדש
            client_service.create_client(
                full_name=full_name,
                id_number=id_number,
                client_type=client_type,
                phone=phone,
                email=email,
                opened_at=date.today(),
            )
            created_count += 1
            
        except Exception as e:
            errors.append({
                "row": row,
                "error": str(e)
            })
    
    return {
        "created": created_count,
        "errors": errors,
        "total_rows": ws.max_row - 1
    }
```

---

## התקנת חבילות נדרשות

```bash
# חבילות לייצוא דוחות
pip install openpyxl reportlab

# חבילות אופציונליות לעיבוד PDF
pip install PyPDF2
```

---

## סיכום ושיפורים עתידיים

### ✅ מה שהושלם
1. דוח חובות ללקוחות (Aging Report)
2. ייצוא לאקסל ו-PDF
3. מערכת תזכורות פרואקטיבית
4. תצוגת PDF בתוך המערכת
5. ייבוא/ייצוא Excel

### 🔜 שיפורים מוצעים לעתיד
1. **תבניות דוחות מותאמות אישית** - אפשרות להגדיר תבניות דוחות
2. **דוחות מתוזמנים** - שליחת דוחות אוטומטית במייל
3. **דשבורד אנליטי** - גרפים אינטראקטיביים של נתוני החובות
4. **אינטגרציה עם מערכות חשבשבת** - סנכרון אוטומטי
5. **OCR למסמכים** - זיהוי טקסט אוטומטי במסמכים סרוקים