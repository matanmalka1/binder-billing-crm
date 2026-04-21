from __future__ import annotations

from random import Random

EMAIL_DOMAIN = "demo-accounting.com"
INVOICE_BASE_URL = "https://files.demo-accounting.test/invoices"

MOBILE_PREFIXES = ["050", "052", "053", "054", "055", "058"]
OFFICE_PHONE_PREFIXES = ["03", "04", "08", "09"]

REALISTIC_ADDRESSES = [
    {"street": "אבן גבירול", "city": "תל אביב-יפו", "zip_code": "6407801"},
    {"street": "דרך מנחם בגין", "city": "תל אביב-יפו", "zip_code": "6713818"},
    {"street": "יפו", "city": "ירושלים", "zip_code": "9438301"},
    {"street": "הנביאים", "city": "חיפה", "zip_code": "3310202"},
    {"street": "העצמאות", "city": "אשדוד", "zip_code": "7710001"},
    {"street": "רוטשילד", "city": "ראשון לציון", "zip_code": "7528805"},
    {"street": "ויצמן", "city": "כפר סבא", "zip_code": "4426102"},
    {"street": "הרצל", "city": "נתניה", "zip_code": "4230507"},
    {"street": "בן יהודה", "city": "באר שבע", "zip_code": "8424904"},
    {"street": "שדרות ירושלים", "city": "חולון", "zip_code": "5845306"},
]

BUSINESS_CATALOG = [
    "אופק פתרונות פיננסיים בע\"מ",
    "גפן לוגיסטיקה ושילוח בע\"מ",
    "תבל שיווק דיגיטלי בע\"מ",
    "ארז מערכות מיזוג בע\"מ",
    "קו חוף ייבוא וסחר בע\"מ",
    "פסגה הנדסה וניהול בע\"מ",
    "ברק ציוד רפואי בע\"מ",
    "רימון מזון ואירוח בע\"מ",
    "שקד עיצוב פנים בע\"מ",
    "לב העיר אחזקות בע\"מ",
]

CLIENT_NOTES = [
    "",
    "מעדיף עדכונים בוואטסאפ בשעות הבוקר",
    "מבקש ריכוז מסמכים אחת לחודש",
    "נדרש מעקב לפני מועדי דיווח רבעוניים",
    "המסמכים מתקבלים בדרך כלל דרך פורטל הלקוחות",
]

BUSINESS_NOTES = [
    "",
    "פעילות יציבה לאורך השנה",
    "נדרש מעקב גבייה חודשי",
    "קיים עומס עונתי ברבעון האחרון",
    "הלקוח מבקש תיאום לפני כל הגשה",
]

ENTITY_NOTE_TEXTS = [
    "הלקוח מקפיד לשלוח מסמכים עד ה-10 בכל חודש",
    "נדרש לוודא התאמה בין דפי הבנק להנהלת החשבונות",
    "התקבל ייפוי כוח מעודכן בתחילת השנה",
    "קיים איש קשר קבוע מול רשות המסים",
    "הלקוח מעדיף סיכום טלפוני לפני שליחת טפסים לחתימה",
]

ACCOUNTANT_NAMES = [
    "רו\"ח דנה לוי",
    "רו\"ח אמיר כהן",
    "רו\"ח נטע מזרחי",
    "רו\"ח הילה ברק",
    "רו\"ח שי אברמוב",
]

AUTHORITY_CONTACTS = [
    {"name": "אילה בן דוד", "office": "פקיד שומה תל אביב 1", "email": "ayala.bendavid@tax.demo-accounting.com"},
    {"name": "אופיר צדוק", "office": "משרד מע\"מ ירושלים", "email": "ofir.tsadok@tax.demo-accounting.com"},
    {"name": "ניב רחמים", "office": "ביטוח לאומי חיפה", "email": "niv.rahamim@btl.demo-accounting.com"},
    {"name": "מורן טל", "office": "משרד מע\"מ באר שבע", "email": "moran.tal@tax.demo-accounting.com"},
    {"name": "סיון הדר", "office": "פקיד שומה נתניה", "email": "sivan.hadar@tax.demo-accounting.com"},
]

CORRESPONDENCE_SUBJECTS = [
    "בירור סטטוס טיפול בבקשת פריסה",
    "השלמת מסמכים לתיק שנתי",
    "עדכון לגבי דוח שהוגש במערכת שע\"ם",
    "תיאום פגישה עם נציג הרשות",
    "בירור לגבי חוב פתוח והצעת הסדרה",
]

CORRESPONDENCE_NOTES = [
    None,
    "המשך טיפול נקבע לשבוע הבא",
    "הסיכום הועבר ללקוח לאחר השיחה",
    "ממתינים למסמך משלים לפני תגובה",
    "נציג הרשות ביקש מסמכים נוספים במייל חוזר",
]

CHARGE_DESCRIPTIONS = [
    None,
    "שכר טרחה חודשי עבור הנהלת חשבונות",
    "טיפול בהגשת דיווח תקופתי",
    "עבודת הנה\"ח והשלמות מסמכים",
    "טיפול נקודתי מול רשות המסים",
]

VAT_COUNTERPARTIES = [
    "שקד מדיה בע\"מ",
    "אלון ציוד משרדי בע\"מ",
    "פסיפס פרסום ודיגיטל בע\"מ",
    "י. כהן שירותי הובלה",
    "מסגריית הדרום בע\"מ",
    "לב השרון שיווק והפצה בע\"מ",
    "גל ים סחר בינלאומי בע\"מ",
    "אפק מערכות מחשוב בע\"מ",
]

DOCUMENT_NOTES = [
    None,
    "נסרק באיכות טובה",
    "התקבל עותק מעודכן מהלקוח",
    "נבדק מול המסמך המקורי",
    "מצורף לתיק הקבוע של הלקוח",
]


def demo_email(prefix: str, serial: int) -> str:
    return f"{prefix}{serial:03d}@{EMAIL_DOMAIN}"


def mobile_phone(rng: Random) -> str:
    prefix = rng.choice(MOBILE_PREFIXES)
    return f"{prefix}{rng.randint(1000000, 9999999)}"


def office_phone(rng: Random) -> str:
    prefix = rng.choice(OFFICE_PHONE_PREFIXES)
    return f"{prefix}-{rng.randint(1000000, 9999999)}"
