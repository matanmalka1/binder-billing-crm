# Sprint 9 Architecture Diagram

## Proper Layering: API → Service → Repository → ORM

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                           │
│                    POST /api/v1/reminders                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (Router)                          │
│                   app/api/reminders.py                           │
│                                                                  │
│  Responsibilities:                                               │
│  ✅ Request/response handling                                   │
│  ✅ HTTP status codes                                           │
│  ✅ Authorization guards (require_role)                         │
│  ✅ Pydantic validation                                         │
│                                                                  │
│  NOT Allowed:                                                    │
│  ❌ Business logic                                              │
│  ❌ Data access                                                 │
│  ❌ Calculations                                                │
│                                                                  │
│  Code:                                                           │
│    @router.post("", response_model=ReminderResponse)            │
│    def create_reminder(request: ReminderCreateRequest, ...):    │
│        service = ReminderService(db)                            │
│        try:                                                      │
│            reminder = service.create_tax_deadline_reminder(...) │
│            return ReminderResponse.model_validate(reminder)     │
│        except ValueError as e:                                   │
│            raise HTTPException(status_code=400, detail=str(e))  │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ delegates to
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER (Business Logic)               │
│                  app/services/reminder_service.py                │
│                                                                  │
│  Responsibilities:                                               │
│  ✅ ALL business logic                                          │
│  ✅ Validation (client exists, dates valid)                     │
│  ✅ Calculations (send_on = target_date - days_before)          │
│  ✅ Default values (message generation)                         │
│  ✅ State transitions                                           │
│                                                                  │
│  NOT Allowed:                                                    │
│  ❌ Direct ORM access (db.add, db.commit, db.query)            │
│  ❌ HTTP concerns                                               │
│  ❌ Request/response formatting                                 │
│                                                                  │
│  Code:                                                           │
│    def create_tax_deadline_reminder(                            │
│        self, client_id, tax_deadline_id, target_date, ...       │
│    ) -> Reminder:                                               │
│        # Validate client exists                                 │
│        client = self.client_repo.get_by_id(client_id)          │
│        if not client:                                           │
│            raise ValueError(f"Client {client_id} not found")   │
│                                                                  │
│        # Calculate send date                                    │
│        send_on = target_date - timedelta(days=days_before)     │
│                                                                  │
│        # Generate default message                               │
│        if message is None:                                      │
│            message = f"תזכורת: מועד מס בעוד {days_before} ..."│
│                                                                  │
│        # Create via repository                                  │
│        return self.reminder_repo.create(...)                   │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ uses
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  REPOSITORY LAYER (Data Access)                  │
│               app/repositories/reminder_repository.py            │
│                                                                  │
│  Responsibilities:                                               │
│  ✅ Data access via ORM                                         │
│  ✅ CRUD operations                                             │
│  ✅ Query construction                                          │
│  ✅ Pagination                                                  │
│                                                                  │
│  NOT Allowed:                                                    │
│  ❌ Business rules                                              │
│  ❌ Validation                                                  │
│  ❌ Calculations                                                │
│                                                                  │
│  Code:                                                           │
│    def create(                                                   │
│        self, client_id, reminder_type, target_date, ...         │
│    ) -> Reminder:                                               │
│        reminder = Reminder(                                     │
│            client_id=client_id,                                 │
│            reminder_type=reminder_type,                         │
│            target_date=target_date,                             │
│            days_before=days_before,                             │
│            send_on=send_on,                                     │
│            message=message,                                     │
│            status=ReminderStatus.PENDING,                       │
│        )                                                        │
│        self.db.add(reminder)                                    │
│        self.db.commit()                                         │
│        self.db.refresh(reminder)                                │
│        return reminder                                          │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ uses
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORM LAYER (Models)                          │
│                    app/models/reminder.py                        │
│                                                                  │
│  Responsibilities:                                               │
│  ✅ Data structure definition                                   │
│  ✅ Table schema                                                │
│  ✅ Relationships                                               │
│  ✅ Indexes                                                     │
│                                                                  │
│  NOT Allowed:                                                    │
│  ❌ Business logic                                              │
│  ❌ Validation                                                  │
│  ❌ Methods (except __repr__)                                   │
│                                                                  │
│  Code:                                                           │
│    class Reminder(Base):                                        │
│        __tablename__ = "reminders"                              │
│                                                                  │
│        id = Column(Integer, primary_key=True)                   │
│        client_id = Column(Integer, ForeignKey("clients.id"))   │
│        reminder_type = Column(Enum(ReminderType))              │
│        status = Column(Enum(ReminderStatus))                   │
│        target_date = Column(Date, nullable=False)              │
│        days_before = Column(Integer, nullable=False)           │
│        send_on = Column(Date, nullable=False)                  │
│        message = Column(Text, nullable=False)                  │
│        # ... timestamps                                         │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                         DATABASE (PostgreSQL)
```

## Request Flow Example

### Creating a Tax Deadline Reminder

```
1. CLIENT
   ↓
   POST /api/v1/reminders
   {
     "client_id": 123,
     "reminder_type": "tax_deadline_approaching",
     "target_date": "2025-03-01",
     "days_before": 7,
     "tax_deadline_id": 456
   }

2. API LAYER (reminders.py)
   ↓
   - Validates request via Pydantic
   - Checks authorization
   - Delegates to service
   
   service = ReminderService(db)
   reminder = service.create_tax_deadline_reminder(...)

3. SERVICE LAYER (reminder_service.py)
   ↓
   - Validates client exists
   - Calculates send_on = 2025-02-22 (7 days before)
   - Generates default message
   - Delegates to repository
   
   client = self.client_repo.get_by_id(123)
   send_on = target_date - timedelta(days=7)
   message = "תזכורת: מועד מס בעוד 7 ימים (2025-03-01)"
   reminder = self.reminder_repo.create(...)

4. REPOSITORY LAYER (reminder_repository.py)
   ↓
   - Creates ORM object
   - Persists to database
   - Returns entity
   
   reminder = Reminder(
       client_id=123,
       reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
       target_date=date(2025, 3, 1),
       days_before=7,
       send_on=date(2025, 2, 22),
       message="תזכורת: מועד מס בעוד 7 ימים...",
   )
   self.db.add(reminder)
   self.db.commit()
   return reminder

5. ORM LAYER (models/reminder.py)
   ↓
   - Maps to database table
   - Executes INSERT
   
   INSERT INTO reminders (
       client_id, reminder_type, target_date,
       days_before, send_on, message, status
   ) VALUES (123, 'tax_deadline_approaching', ...)

6. DATABASE
   ↓
   - Stores record
   - Returns ID
   
   Reminder ID: 789 created

7. RESPONSE FLOW (back up the stack)
   ↓
   Repository → Service → API → Client
   
   HTTP 201 Created
   {
     "id": 789,
     "client_id": 123,
     "reminder_type": "tax_deadline_approaching",
     "status": "pending",
     "target_date": "2025-03-01",
     "send_on": "2025-02-22",
     ...
   }
```

## Key Principles

### ✅ DO
- **API**: Handle HTTP concerns only
- **Service**: Implement all business logic
- **Repository**: Access data via ORM only
- **ORM**: Define structure only

### ❌ DON'T
- **API**: Make business decisions
- **Service**: Access database directly
- **Repository**: Implement business rules
- **ORM**: Contain methods or logic

## Benefits

### Separation of Concerns ✅
- Each layer has single responsibility
- Changes isolated to appropriate layer
- Easy to test independently

### Maintainability ✅
- Clear where to add features
- Easy to find code
- Consistent patterns

### Testability ✅
- Mock at layer boundaries
- Unit test each layer
- Integration test full stack

### Reusability ✅
- Services reusable across endpoints
- Repositories reusable across services
- Models reusable across app

## Comparison: Before vs After

### BEFORE (VIOLATED) ❌
```
API Layer (reminders.py)
  ├─ Business logic (type routing)
  ├─ Calculations (send_on)
  └─ Default values (message)
  
Service Layer (reminder_service.py)
  ├─ Direct ORM access (db.add, db.commit)
  └─ Skipped repository layer
  
Repository Layer
  └─ MISSING ❌

ORM Layer (models/reminder.py)
  └─ OK ✅
```

### AFTER (COMPLIANT) ✅
```
API Layer (reminders.py)
  ├─ Request validation
  ├─ Authorization
  └─ Delegation only
  
Service Layer (reminder_service.py)
  ├─ Business logic
  ├─ Validation
  ├─ Calculations
  └─ Uses repository only
  
Repository Layer (reminder_repository.py)
  ├─ Data access
  ├─ ORM operations
  └─ Query construction
  
ORM Layer (models/reminder.py)
  └─ Data structure only
```

## Success Criteria Met ✅

- ✅ All layers present
- ✅ Proper separation of concerns
- ✅ No layer skipping
- ✅ No business logic in API
- ✅ No direct ORM in service
- ✅ All files under 150 lines
- ✅ Follows PROJECT_RULES.md

**Status: ARCHITECTURE COMPLIANT** ✅
