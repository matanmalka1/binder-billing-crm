-- Migration: Add Reminders Table
-- Description: Proactive reminder system for tax deadlines, idle binders, and unpaid charges
-- Date: 2026-02-16
-- Sprint: 7+

-- Create reminders table
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    reminder_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    
    -- Dates
    target_date DATE NOT NULL,
    days_before INTEGER NOT NULL,
    send_on DATE NOT NULL,
    
    -- References to related entities
    binder_id INTEGER,
    charge_id INTEGER,
    tax_deadline_id INTEGER,
    
    -- Message content
    message TEXT NOT NULL,
    
    -- Tracking
    created_at DATETIME NOT NULL,
    sent_at DATETIME,
    canceled_at DATETIME,
    
    -- Foreign keys
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (binder_id) REFERENCES binders(id),
    FOREIGN KEY (charge_id) REFERENCES charges(id),
    FOREIGN KEY (tax_deadline_id) REFERENCES tax_deadlines(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_reminder_client 
    ON reminders(client_id);

CREATE INDEX IF NOT EXISTS idx_reminder_binder 
    ON reminders(binder_id);

CREATE INDEX IF NOT EXISTS idx_reminder_charge 
    ON reminders(charge_id);

CREATE INDEX IF NOT EXISTS idx_reminder_tax_deadline 
    ON reminders(tax_deadline_id);

CREATE INDEX IF NOT EXISTS idx_reminder_status_send_on 
    ON reminders(status, send_on);

CREATE INDEX IF NOT EXISTS idx_reminder_target_date 
    ON reminders(target_date);

CREATE INDEX IF NOT EXISTS idx_reminder_send_on 
    ON reminders(send_on);

-- Verify table creation
SELECT 'Reminders table created successfully' AS status;

-- Check table structure
PRAGMA table_info(reminders);