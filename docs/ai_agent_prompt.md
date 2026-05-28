# פרומפט קבוע לסוכן AI בפרויקט

העתק את הפרומפט הבא בתחילת כל עבודה עם סוכן AI על הפרויקט.

```text
אתה עובד על פרויקט Binder & Billing CRM.

לפני כל שינוי בקוד או במסמכים, קרא את חוקי הבסיס של הפרויקט:
1. קרא את `AGENTS.md` במלואו.
2. פעל לפי הכללים שם כמקור אמת מחייב.
3. אם יש סתירה בין בקשה נקודתית לבין `AGENTS.md`, עצור והצף את הסתירה לפני שינוי.
4. אל תניח מבנה, חוזה API, הרשאות, או התנהגות קיימת בלי לבדוק את הקוד והמסמכים הרלוונטיים.


כללי עבודה מחייבים:

- Backend: FastAPI, SQLAlchemy ORM, Pydantic v2.
- אין raw SQL.
- שמור על שכבות: API -> Service -> Repository -> ORM.
- אין לוגיקה עסקית ב-router.
- אין imports בין domains ברמת Repository או Model.
- כל endpoint רגיש חייב לבצע בדיקת הרשאות ו-business ownership.
- כל list endpoint חדש חייב לתמוך ב-pagination, filtering, sorting לפי הסטנדרט.
- כל שינוי schema חייב לעבור דרך Alembic.
- השתמש ב-virtualenv של הריפו בלבד:
  `APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python -m ...`
- אל תשתמש ב-global `python` או `python3` בתוך backend.
- הודעות שמוצגות למשתמש חייבות להיות בעברית.
- UI בפרונטנד הוא Hebrew-only.

לפני עבודה לפי תחום, קרא גם את המסמכים הרלוונטיים:

- חוזי API: `docs/api-contract-standard.md`
- מסכי frontend: `docs/frontend_screen_spec.md`
- ריפקטור lifecycle של קלסרים: `docs/binder_lifecycle_refactor_spec.md`
- מקדמות מס הכנסה: `docs/advance_payments_spec.md`
- היסטוריה מול timeline: `docs/history-vs-timeline.md`, `docs/history-map.md`
- חוקי מס ישראליים: השתמש רק ב-`tax_rules_config/`, לא בערכים hardcoded בתוך `app/`

אם המשימה נוגעת לפרונטנד:

- בדוק גם את `../frontend`.
- שמור enum fields מסונכרנים: backend enum -> frontend `z.enum([...])`.
- הגדר enum arrays ב-`constants.ts`, לא inline בקומפוננטות או schemas.
- אל תשכפל סמכות עסקית בפרונטנד אם backend כבר מחזיר actions או state derived.

אם המשימה נוגעת ל-auth בדפדפן:

- העדף access token בזיכרון בלבד.
- refresh token צריך להיות HttpOnly cookie מה-backend.
- אל תשמור tokens ב-localStorage או sessionStorage אלא אם ניתנה הוראה מפורשת.
- בפריסה עם SPA ו-API נפרדים, העדף same-origin proxy/rewrite ל-API כדי לא להישען על cross-site cookies.

תהליך עבודה:

1. קרא את ההנחיות והמסמכים הרלוונטיים.
2. בדוק את הקוד הקיים וה-patterns לפני הצעה או שינוי.
3. בצע שינוי קטן וממוקד.
4. הרץ בדיקות רלוונטיות בלבד כברירת מחדל.
5. דווח בסוף:
   - מה השתנה
   - אילו קבצים נגעו
   - אילו בדיקות הורצו
   - מה נשאר פתוח, אם יש

אל תשאיר TODOs שמחזירים legacy behavior.
אל תיצור compatibility layer אלא אם נדרש במפורש.
אל תשנה קבצים לא קשורים.
```

## שימוש מומלץ

- למשימת backend כללית: הדבק את הפרומפט ואז הוסף את תיאור המשימה.
- למשימת frontend: הדבק את הפרומפט והוסף במפורש שהסוכן צריך לבדוק גם את `../frontend`.
- למשימה גדולה: בקש מהסוכן להתחיל ב-plan קצר אחרי קריאת המסמכים, ורק אז לבצע.
- למשימת review: בקש findings לפי חומרה עם הפניות לקובץ ושורה.
