# Surplus Med Decision System - Quick Start Guide

## How to Run the System

1. Navigate to the project directory:
```bash
cd /Users/shashankjagannatham/Documents/Shivani/Projects/Surplus-Med/sur-med/surmed
```

2. Start the development server:
```bash
python manage.py runserver
```

3. Access the system:
- Healthcare Dashboard: http://127.0.0.1:8000/decision/
- Admin Interface: http://127.0.0.1:8000/admin/

## Login Credentials

Admin Account:
- Username: admin
- Password: admin123

Note: This admin user has full access to make final decisions.

## Key Features for NGOs and Healthcare Departments

### 1. Dashboard
Access at: http://127.0.0.1:8000/decision/

Shows:
- Pending review statistics
- Accepted, needs review, and rejected counts
- List of supplies awaiting decisions
- Recent decision history

### 2. Submit Medical Supply
Navigate: Dashboard -> Submit New Supply

Required information:
- Item name and category
- Quantity and unit
- Expiry date
- Packaging status
- Storage conditions
- Evidence files (photos, documents)

The system automatically:
- Generates unique Supply ID
- Runs eligibility checks
- Creates audit log entry

### 3. Review and Make Decisions
Navigate: Dashboard -> Review button on any supply

Decision interface provides:
- Complete supply information
- Automated eligibility assessment
- Evidence documentation viewer
- Decision history
- Three decision options:
  1. Accept for Redistribution
  2. Needs Additional Review
  3. Reject

Every decision requires:
- Reason code selection
- Detailed justification (for audit trail)
- Optional additional notes

### 4. Audit Log
Navigate: Dashboard -> Audit Log

Features:
- Complete decision history
- Filter by date range, decision type, or search
- Export to CSV or PDF
- Statistics dashboard
- Immutable records

### 5. Export Reports
From Audit Log page:
- Export CSV: Complete data export for analysis
- Export PDF: Formatted audit report for official use

## Eligibility Rules (Pre-configured)

The system includes these rules:

1. Minimum Shelf Life: 60 days remaining until expiry
2. No Prescription Drugs: Only allows specific categories
3. Packaging Integrity: Must be sealed or have minimal damage
4. Photo Evidence: Recommends photographic documentation
5. Quantity Minimum: At least 1 unit required

Manage rules: Dashboard -> Rules (staff only)

## Reason Codes (Pre-configured)

### Acceptance Codes
- ACC-001: Meets all criteria
- ACC-002: Acceptable with minor concerns
- ACC-003: Priority acceptance

### Review Codes
- REV-001: Insufficient documentation
- REV-002: Packaging concerns
- REV-003: Storage conditions unclear
- REV-004: Requires specialist review

### Rejection Codes
- REJ-001: Expired supply
- REJ-002: Insufficient shelf life
- REJ-003: Damaged packaging
- REJ-004: Prescription medication
- REJ-005: Missing batch information
- REJ-006: Category not accepted

## Admin Interface

Access at: http://127.0.0.1:8000/admin/

Manage:
- Supplies
- Decisions
- Evidence files
- Reason codes
- Eligibility rules
- Audit logs
- Users and permissions

## Multi-Tier Approval System

The system supports two decision levels:

1. Initial Review: Regular users make initial assessments
2. Final Approval: Staff users (is_staff=True) make final decisions

Configure user permissions in Admin -> Users

## Creating Additional Users

1. Go to Admin Interface
2. Click Users -> Add User
3. Set username and password
4. Optionally grant staff status for final approval rights
5. Save

## Data Model Highlights

Every supply has:
- Unique Supply ID (auto-generated)
- Chain of custody hash
- Complete submission history
- Decision records (immutable)
- Evidence attachments with file integrity hashes

Every decision includes:
- Decision type (Accept/Review/Reject)
- Reason code
- Justification
- Decision maker
- Timestamp
- Eligibility assessment snapshot
- Cryptographic hash for integrity

## File Structure

decision_system/
- models.py: Supply, Decision, Evidence, ReasonCode, EligibilityRule, AuditLog
- views.py: All business logic and request handlers
- eligibility.py: Rule-based validation engine
- urls.py: URL routing
- admin.py: Django admin configuration
- templates/: All UI templates
- static/: CSS and JavaScript
- management/commands/: Seed data command

## Important Notes

- All decisions are immutable and cannot be deleted
- Audit logs are read-only
- File uploads are stored in media/evidence/
- Database is SQLite (upgrade to PostgreSQL for production)
- PDF export requires reportlab library
