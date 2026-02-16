# 📦 חבילת תכונות חדשות - מערכת CRM יועץ מס

## סקירה מהירה

חבילה זו מוסיפה למערכת הקיימת:

✅ **דוח חובות ללקוחות (Aging Report)** - ניתוח חובות לפי גיל  
✅ **ייצוא לExcel/PDF** - ייצוא כל הדוחות  
✅ **מערכת תזכורות פרואקטיבית** - X ימים לפני מועדים  
✅ **תצוגת PDF** - צפייה במסמכים בתוך המערכת  
✅ **ייבוא/ייצוא Excel** - העברת נתונים בקלות

---

## 📁 תוכן החבילה

### קבצי Backend (Python)

#### 1. Models

- `app_models_reminder.py` → `app/models/reminder.py`
  - מודל תזכורות עם סטטוסים ומועדים

#### 2. Services (Business Logic)

- `app_services_reports.py` → `app/services/reports_service.py`
  - **AgingReportService** - דוח חובות ללקוחות
- `app_services_export.py` → `app/services/export_service.py`
  - **ExportService** - ייצוא לExcel ו-PDF
- `app_services_reminder.py` → `app/services/reminder_service.py`
  - **ReminderService** - ניהול תזכורות

#### 3. API Endpoints

- `app_api_reports.py` → `app/api/reports.py`
  - `GET /api/v1/reports/aging` - קבלת דוח חובות
  - `GET /api/v1/reports/aging/export` - ייצוא דוח

#### 4. Schemas (Pydantic)

- `app_schemas_reports.py` → `app/schemas/reports.py`
  - AgingReportResponse, AgingReportItem, וכו'

### תיעוד

- `INSTALLATION_GUIDE.md` - **התחל כאן!** מדריך התקנה מפורט
- `FEATURES_DOCUMENTATION.md` - תיעוד טכני מלא
- `README.md` - הקובץ הזה

---

## 🚀 התקנה מהירה (5 דקות)

### שלב 1: התקן חבילות

```bash
pip install openpyxl reportlab
```

### שלב 2: העתק קבצים

```bash
# בנוהו אוטומטי (Linux/Mac)
cp app_models_reminder.py ./app/models/reminder.py
cp app_services_reports.py ./app/services/reports_service.py
cp app_services_export.py ./app/services/export_service.py
cp app_services_reminder.py ./app/services/reminder_service.py
cp app_api_reports.py ./app/api/reports.py
cp app_schemas_reports.py ./app/schemas/reports.py

# Windows
copy app_models_reminder.py app\models\reminder.py
copy app_services_reports.py app\services\reports_service.py
copy app_services_export.py app\services\export_service.py
copy app_services_reminder.py app\services\reminder_service.py
copy app_api_reports.py app\api\reports.py
copy app_schemas_reports.py app\schemas\reports.py
```

### שלב 3: עדכן imports

#### `app/models/__init__.py`

```python
from app.models.reminder import Reminder, ReminderType, ReminderStatus

__all__ = [
    # ... קיים
    "Reminder", "ReminderType", "ReminderStatus",
]
```

#### `app/api/__init__.py`

```python
from app.api import reports

__all__ = [
    # ... קיים
    "reports",
]
```

#### `app/main.py`

```python
from app.api import reports

app.include_router(reports.router, prefix="/api/v1")
```

### שלב 4: בסיס נתונים

**Development:**

```bash
rm binder_crm.db
APP_ENV=development python -m app.main
```

**Production:** הרץ SQL מ-INSTALLATION_GUIDE.md

### שלב 5: בדיקה

```bash
# הפעל את השרת
python -m app.main

# בדוק ב-browser
http://localhost:8000/docs
# חפש "reports" - אמור להיות 2 endpoints
```

---

## 💡 דוגמאות שימוש

### דוח חובות ללקוחות

```bash
curl -X GET "http://localhost:8000/api/v1/reports/aging" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### ייצוא לExcel

```bash
curl -X GET "http://localhost:8000/api/v1/reports/aging/export?format=excel" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### יצירת תזכורת (Python)

```python
from app.services.reminder_service import ReminderService

reminder = reminder_service.create_tax_deadline_reminder(
    client_id=123,
    tax_deadline_id=456,
    target_date=date(2026, 3, 15),
    days_before=7,  # 7 ימים לפני
)
```

---

## 📊 מה כלול?

### 1. דוח חובות (Aging Report)

- חלוקה לפי גיל חוב: 0-30, 31-60, 61-90, 90+ ימים
- סיכום כולל וסיכום לפי לקוח
- תאריך החוב העתיק ביותר
- **API:** `GET /api/v1/reports/aging`

### 2. ייצוא דוחות

- **Excel:** טבלאות מעוצבות עם צבעים וכותרות
- **PDF:** מסמכים מקצועיים להדפסה
- **API:** `GET /api/v1/reports/aging/export?format=excel|pdf`

### 3. מערכת תזכורות

- תזכורת X ימים לפני מועד מס
- תזכורת לתיק שלא טופל X ימים
- תזכורת לחשבונית שלא שולמה X ימים
- **Job יומי אוטומטי** (צריך להגדיר)

### 4. תצוגת PDF

- צפייה במסמכים ישירות בדפדפן
- הורדה אופציונלית
- **דוגמה ב-FEATURES_DOCUMENTATION.md**

### 5. ייבוא/ייצוא Excel

- ייבוא רשימת לקוחות
- ייצוא נתונים לעיבוד חיצוני
- **דוגמאות קוד ב-FEATURES_DOCUMENTATION.md**

---

## 🏗️ ארכיטקטורה

התכונות עוקבות אחר העקרונות של המערכת הקיימת:

✅ **API → Service → Repository → ORM**  
✅ **≤ 150 שורות לקובץ**  
✅ **ללא SQL ישיר (ORM בלבד)**  
✅ **Derived state (חישובים דינמיים)**  
✅ **הרשאות: ADVISOR בלבד לדוחות פיננסיים**

---

## 📖 תיעוד נוסף

### קרא קודם: `INSTALLATION_GUIDE.md`

- מדריך התקנה צעד אחר צעד
- פתרון בעיות נפוצות
- Checklist מלא

### תיעוד מפורט: `FEATURES_DOCUMENTATION.md`

- הסברים טכניים מעמיקים
- דוגמאות קוד מלאות
- אינטגרציה עם Frontend
- Job אוטומטי יומי
- שיפורים עתידיים

---

## 🎯 Checklist מהיר

- [ ] `pip install openpyxl reportlab`
- [ ] העתק 6 קבצי Python
- [ ] עדכן 3 קבצי **init**.py
- [ ] רשום router ב-main.py
- [ ] צור טבלת reminders (SQL או ORM)
- [ ] צור תיקייה `/tmp/exports`
- [ ] הפעל שרת ובדוק `/docs`
- [ ] נסה endpoint: `GET /api/v1/reports/aging`

---

## ⚠️ דרישות מערכת

- Python 3.14+
- FastAPI (קיים)
- SQLAlchemy (קיים)
- openpyxl (חדש)
- reportlab (חדש)
- PyPDF2 (אופציונלי)

---

## 🆘 צריך עזרה?

1. **בעיות התקנה** → `INSTALLATION_GUIDE.md` סעיף "פתרון בעיות"
2. **שאלות טכניות** → `FEATURES_DOCUMENTATION.md`
3. **דוגמאות קוד** → שני מסמכי התיעוד
4. **שגיאות בהרצה** → בדוק logs, בדוק `/docs`

---

## 🔄 עדכונים עתידיים מוצעים

- [ ] תבניות דוחות מותאמות אישית
- [ ] דוחות מתוזמנים (שליחה אוטומטית במייל)
- [ ] דשבורד אנליטי אינטראקטיבי
- [ ] אינטגרציה עם מערכות חשבשבת
- [ ] OCR למסמכים סרוקים

---

## 📄 רשיון

חלק ממערכת Binder & Billing CRM  
Sprint 7+ - התכונות החדשות

---

**הצלחה! 🎉**

כל הקבצים מוכנים לשימוש. התחל עם `INSTALLATION_GUIDE.md`
