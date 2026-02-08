# מדריך אינטגרציה - Sprint 2

## שלב 1: הוסף את הקבצים החדשים

העתק את 11 הקבצים החדשים למיקומים הבאים:

```
app/
├── services/
│   ├── sla_service.py                        ← חדש
│   ├── binder_operations_service.py          ← חדש
│   ├── dashboard_overview_service.py         ← חדש
│   └── binder_history_service.py             ← חדש
├── repositories/
│   └── binder_repository_sprint2.py          ← חדש
├── schemas/
│   ├── binder_sprint2.py                     ← חדש
│   └── dashboard_sprint2.py                  ← חדש
└── api/
    ├── binders_operations.py                 ← חדש
    ├── clients_binders.py                    ← חדש
    ├── dashboard_overview.py                 ← חדש
    └── binders_history.py                    ← חדש
```

## שלב 2: עדכן app/services/__init__.py

**הוסף את השורות הבאות** לקובץ הקיים:

```python
from app.services.sla_service import SLAService
from app.services.binder_operations_service import BinderOperationsService
from app.services.dashboard_overview_service import DashboardOverviewService
from app.services.binder_history_service import BinderHistoryService
```

ועדכן את __all__:

```python
__all__ = [
    "AuthService",
    "ClientService",
    "BinderService",
    "DashboardService",
    "SLAService",                              # ← חדש
    "BinderOperationsService",                 # ← חדש
    "DashboardOverviewService",                # ← חדש
    "BinderHistoryService",                    # ← חדש
]
```

## שלב 3: עדכן app/schemas/__init__.py

**הוסף את השורות הבאות**:

```python
from app.schemas.dashboard_sprint2 import DashboardOverviewResponse
from app.schemas.binder_sprint2 import (
    BinderDetailResponse,
    BinderListResponseSprint2,
    BinderHistoryEntry,
    BinderHistoryResponse,
)
```

ועדכן את __all__:

```python
__all__ = [
    "LoginRequest",
    "LoginResponse",
    "UserResponse",
    "ClientCreateRequest",
    "ClientUpdateRequest",
    "ClientResponse",
    "ClientListResponse",
    "BinderReceiveRequest",
    "BinderReturnRequest",
    "BinderResponse",
    "BinderListResponse",
    "DashboardSummaryResponse",
    "DashboardOverviewResponse",               # ← חדש
    "BinderDetailResponse",                    # ← חדש
    "BinderListResponseSprint2",               # ← חדש
    "BinderHistoryEntry",                      # ← חדש
    "BinderHistoryResponse",                   # ← חדש
]
```

## שלב 4: עדכן app/api/__init__.py

**הוסף את השורות הבאות**:

```python
from app.api import (
    auth,
    clients,
    binders,
    dashboard,
    binders_operations,        # ← חדש
    clients_binders,           # ← חדש
    dashboard_overview,        # ← חדש
    binders_history,           # ← חדש
)

__all__ = [
    "auth",
    "clients",
    "binders",
    "dashboard",
    "binders_operations",      # ← חדש
    "clients_binders",         # ← חדש
    "dashboard_overview",      # ← חדש
    "binders_history",         # ← חדש
]
```

## שלב 5: עדכן app/main.py

**הוסף את ה-routers החדשים** (אחרי ה-routers הקיימים):

```python
# API routes - existing
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(binders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

# API routes - Sprint 2 (חדש!)
app.include_router(binders_operations.router, prefix="/api/v1")
app.include_router(clients_binders.router, prefix="/api/v1")
app.include_router(dashboard_overview.router, prefix="/api/v1")
app.include_router(binders_history.router, prefix="/api/v1")
```

ועדכן את ה-import בראש הקובץ:

```python
from app.api import (
    auth,
    clients,
    binders,
    dashboard,
    binders_operations,        # ← חדש
    clients_binders,           # ← חדש
    dashboard_overview,        # ← חדש
    binders_history,           # ← חדש
)
```

## סיכום

✅ **קבצים חדשים**: 11 קבצים להוסיף  
✅ **קבצים לעדכן**: 4 קבצים (רק הוספת שורות, לא החלפה)  
❌ **קבצים להחליף**: אף אחד!

כל הקוד הקיים נשאר בדיוק כמו שהוא. Sprint 2 הוא **additive** - רק מוסיף פונקציונליות חדשה.