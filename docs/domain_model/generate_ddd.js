const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageOrientation
} = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const headerBorder = { style: BorderStyle.SINGLE, size: 1, color: "2E5496" };
const headerBorders = { top: headerBorder, bottom: headerBorder, left: headerBorder, right: headerBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 32, font: "Arial" })],
    spacing: { before: 400, after: 200 }
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial" })],
    spacing: { before: 300, after: 160 }
  });
}

function h3(text) {
  return new Paragraph({
    children: [new TextRun({ text, bold: true, size: 24, font: "Arial", color: "2E5496" })],
    spacing: { before: 240, after: 120 }
  });
}

function p(text, options = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, font: "Arial", ...options })],
    spacing: { before: 80, after: 80 }
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    children: [new TextRun({ text, size: 22, font: "Arial" })],
    spacing: { before: 40, after: 40 }
  });
}

function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 20, font: "Courier New", color: "1F3864" })],
    spacing: { before: 40, after: 40 },
    indent: { left: 720 },
    shading: { fill: "F2F2F2", type: ShadingType.CLEAR }
  });
}

function separator() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E5496", space: 1 } },
    spacing: { before: 200, after: 200 },
    children: []
  });
}

function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => new TableCell({
          borders: headerBorders,
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { fill: "2E5496", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: h, bold: true, size: 20, font: "Arial", color: "FFFFFF" })]
          })]
        }))
      }),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((cell, i) => new TableCell({
          borders,
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { fill: ri % 2 === 0 ? "FFFFFF" : "F5F8FF", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: cell, size: 20, font: "Arial" })]
          })]
        }))
      }))
    ]
  });
}

function sp(n = 1) {
  return Array(n).fill(0).map(() => new Paragraph({ children: [], spacing: { before: 80, after: 80 } }));
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }
        ]
      }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E5496" },
        paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [

      // Title
      new Paragraph({
        children: [new TextRun({ text: "Domain Decision Document", bold: true, size: 48, font: "Arial", color: "1F3864" })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "CRM System for Tax Advisory Firms — Backend Architecture", size: 26, font: "Arial", color: "595959" })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "Version 1.1  |  Status: Draft  |  " + new Date().toLocaleDateString('he-IL'), size: 22, font: "Arial", color: "808080" })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 400 }
      }),

      separator(),

      // Section 1
      h1("1. Target Model"),
      h2("1.1 Entity Map"),
      p("The current Client entity is a mixture of three distinct concepts. The required model separates these into independent entities with clear responsibilities."),
      ...sp(),

      makeTable(
        ["Entity", "Concept", "Responsibility"],
        [
          ["Person", "Physical individual", "Stores personal identity: name, national ID (Israeli), phone, email, address"],
          ["LegalEntity", "Legal/tax entity", "Stores legal identity: registration number, entity type, VAT profile, advance rate"],
          ["ClientRecord", "Office relationship", "Stores operational metadata: office client number, accountant, notes, status"],
          ["Business", "Operational activity", "Represents a named business activity under a LegalEntity"],
          ["PersonLegalEntityLink", "Ownership/role mapping", "Links a Person to one or more LegalEntities with a defined role"],
        ],
        [2000, 2200, 5160]
      ),

      ...sp(2),
      h2("1.2 Entity Definitions"),

      h3("Person"),
      p("Represents the physical individual behind legal entities. Not a tax filer. Not a client."),
      code("Person"),
      code("  id"),
      code("  first_name, last_name"),
      code("  national_id          -- Israeli ID only (expand later if needed)"),
      code("  phone, email"),
      code("  address_street, address_city, address_zip_code"),
      code("  address_building_number, address_apartment"),

      ...sp(),
      h3("LegalEntity"),
      p("Represents the legal/tax entity registered with Israeli authorities. Source of truth for legal identity."),
      code("LegalEntity"),
      code("  id"),
      code("  id_number            -- teudat zehut / osek mursheh / hevra"),
      code("  id_number_type       -- INDIVIDUAL / SELF_EMPLOYED / CORPORATION / etc."),
      code("  entity_type          -- determines VAT and annual report behavior"),
      code("  vat_reporting_frequency"),
      code("  vat_exempt_ceiling"),
      code("  advance_rate, advance_rate_updated_at"),

      ...sp(),
      h3("ClientRecord"),
      p("Represents the office's relationship with a LegalEntity. Created at onboarding. Carries all operational state."),
      code("ClientRecord"),
      code("  id"),
      code("  legal_entity_id      -- FK → LegalEntity"),
      code("  office_client_number"),
      code("  accountant_name"),
      code("  notes"),
      code("  status               -- active / frozen / closed"),
      code("  deleted_at, deleted_by, restored_at, restored_by"),

      ...sp(),
      h3("Business"),
      p("Represents a named operational activity under a LegalEntity. Not a separate legal entity. Does not hold its own tax profile."),
      code("Business"),
      code("  id"),
      code("  legal_entity_id      -- FK → LegalEntity (NOT ClientRecord)"),
      code("  business_name"),
      code("  status"),
      code("  opened_at, closed_at"),
      code("  phone_override, email_override"),
      code("  notes"),

      ...sp(),
      h3("PersonLegalEntityLink"),
      p("Links a Person to one or more LegalEntities. Enables the 'full picture per person' view across entities."),
      code("PersonLegalEntityLink"),
      code("  person_id            -- FK → Person"),
      code("  legal_entity_id      -- FK → LegalEntity"),
      code("  role                 -- owner / authorized_signatory / controlling_shareholder"),

      ...sp(2),
      separator(),

      // Section 2
      h1("2. Ownership Rules"),
      h2("2.1 Primary Anchor Decision"),
      p("The domain is organized around ClientRecord as the operational anchor, not LegalEntity. This reflects the system's purpose: office workflow management, not a legal registry."),

      ...sp(),
      makeTable(
        ["Entity", "Primary Anchor", "Rationale"],
        [
          ["VatReport", "client_record_id", "Exists because the office manages this filing"],
          ["AnnualReport", "client_record_id", "Exists because the office manages this filing"],
          ["TaxDeadline", "client_record_id", "Tied to the office relationship lifecycle"],
          ["Binder", "client_record_id", "Logistical object created by the office"],
          ["Reminder", "client_record_id", "Operational alert created by office staff"],
          ["Document (most)", "client_record_id", "Created in the context of office work"],
          ["Business", "legal_entity_id", "Describes the entity's activity, not office work"],
          ["PersonLegalEntityLink", "legal_entity_id", "Legal/ownership relationship, not office work"],
          ["Documents (legal)", "legal_entity_id", "Permanent legal identity documents"],
        ],
        [2200, 2400, 4760]
      ),

      ...sp(2),
      h2("2.2 Business Usage in Workflow Entities"),
      p("Workflow entities may reference a business_id for tagging/attribution purposes. The following invariant must be enforced at the application layer:"),
      ...sp(),
      new Paragraph({
        children: [new TextRun({ text: "INVARIANT: workflow_entity.business_id → business.legal_entity_id == workflow_entity.client_record_id → client_record.legal_entity_id", size: 20, font: "Courier New", bold: true, color: "C00000" })],
        indent: { left: 720 },
        spacing: { before: 80, after: 80 }
      }),
      ...sp(),
      p("This means: a business referenced within a workflow entity must belong to the same LegalEntity that the ClientRecord is linked to. Violation of this invariant is a data integrity error."),

      ...sp(2),
      separator(),

      // Section 3
      h1("3. Integrity Rules"),
      h2("3.1 The Core Problem"),
      p("The current system uses logical sync based on client_id + period/date to relate workflow entities (VatReport, AnnualReport) to deadline entities (TaxDeadline). This approach is fragile: it relies on date range lookups rather than domain identity, and allows duplicate deadlines to accumulate silently after entity_type changes."),

      ...sp(),
      h2("3.2 Required: Domain Identity Constraints"),
      p("Each obligation must have exactly one identity key per client per period. The following unique constraints replace the current date-range lookup approach:"),

      ...sp(),
      makeTable(
        ["Entity", "Unique Constraint", "Replaces"],
        [
          ["AnnualReport", "(client_record_id, tax_year)", "No uniqueness enforced today"],
          ["TaxDeadline (annual)", "(client_record_id, deadline_type, tax_year)", "Dedup by (client_id, deadline_type, due_date)"],
          ["TaxDeadline (VAT)", "(client_record_id, deadline_type, period)", "Dedup by (client_id, deadline_type, due_date)"],
          ["VatReport", "(client_record_id, period)", "No uniqueness enforced today"],
        ],
        [2200, 3000, 4160]
      ),

      ...sp(2),
      h2("3.3 Sync Logic"),
      p("After introducing domain identity constraints, all sync between AnnualReport/VatReport and TaxDeadline must use the domain key, not date ranges. This fixes both the current AnnualReport/TaxDeadline mismatch and the weaker VAT/TaxDeadline relationship:"),
      ...sp(),
      bullet("Annual: sync via (client_record_id, tax_year)"),
      bullet("VAT: sync via (client_record_id, period)"),
      bullet("Never: sync via due_date range lookup"),

      ...sp(2),
      h2("3.4 entity_type Change Handling"),
      p("Changing entity_type on a LegalEntity is a high-impact operation. The current system allows it silently, causing drift across AnnualReport, TaxDeadline, and Reminder. Required behavior:"),
      ...sp(),
      bullet("entity_type changes must be ADVISOR-only (not SECRETARY)"),
      bullet("On change: existing open TaxDeadlines of type ANNUAL_REPORT must be canceled before regeneration"),
      bullet("On change: existing AnnualReport for the current tax year must be flagged for review (not silently left with stale client_type)"),
      bullet("On change: a warning must be surfaced in the audit log and optionally to the user"),

      ...sp(2),
      h2("3.5 Future: Obligation Entity (Recommended)"),
      p("The ideal model introduces an Obligation entity as the shared identity anchor for both workflow and deadline. This is preferred to a direct FK between AnnualReport and TaxDeadline, because the real missing concept is shared obligation identity, not simple linkage:"),
      ...sp(),
      code("Obligation"),
      code("  id"),
      code("  client_record_id"),
      code("  obligation_type      -- annual_report / vat / advance"),
      code("  period               -- tax_year (annual) or YYYY-MM (VAT)"),
      code("  unique (client_record_id, obligation_type, period)"),
      ...sp(),
      code("AnnualReport  → obligation_id"),
      code("TaxDeadline   → obligation_id"),
      code("VatReport     → obligation_id"),
      ...sp(),
      p("This replaces logical sync with structural linkage, and eliminates all current drift scenarios. Recommended for a future iteration after the current model is stabilized."),

      ...sp(2),
      separator(),

      // Section 4
      h1("4. Lifecycle Policies"),
      h2("4.1 Principle"),
      p("ClientRecord closure does not cascade-delete history. It stops new work creation and transitions operational entities to terminal states. The distinction between cancel, archive, freeze, and preserve is explicit per entity type."),

      ...sp(),
      h2("4.2 Policy Table"),

      makeTable(
        ["Entity", "On ClientRecord Close", "Rationale"],
        [
          ["Reminder (active)", "Cancel automatically", "Operational alerts have no value after closure"],
          ["TaxDeadline (open)", "Mark as canceled", "No new work; preserve audit trail"],
          ["VatReport (non-final)", "Mark as canceled/archived", "Preserve data; stop workflow"],
          ["AnnualReport (non-final)", "Mark as canceled", "Preserve data; stop workflow"],
          ["Binder (open)", "Mark as archived_in_office", "Requires physical handover decision"],
          ["Document", "No change", "Permanent historical record"],
          ["EntityAuditLog", "No change", "Immutable audit trail"],
          ["StatusHistory", "No change", "Immutable history"],
          ["PersonLegalEntityLink", "No change", "Legal ownership facts persist"],
          ["Business", "No cascade", "Office closure ≠ business closure in the world"],
        ],
        [2200, 3000, 4160]
      ),

      ...sp(2),
      h2("4.3 Missing Terminal States"),
      p("The following terminal states do not exist today and must be added to support the lifecycle policy:"),
      ...sp(),
      makeTable(
        ["Entity", "Missing State(s)"],
        [
          ["TaxDeadline", "canceled"],
          ["VatReport", "canceled, archived"],
          ["AnnualReport", "canceled"],
          ["Binder", "archived_in_office"],
        ],
        [3000, 6360]
      ),

      ...sp(2),
      h2("4.4 Block on Closed ClientRecord"),
      p("When ClientRecord.status = closed or frozen, the following operations must be blocked at the service layer:"),
      ...sp(),
      bullet("Creating new VatReport, AnnualReport, TaxDeadline, Binder, Reminder"),
      bullet("Intake of new Binder material"),
      bullet("Creating new Documents (except legal/archival documents with explicit override)"),
      bullet("Generating obligations via DeadlineGeneratorService"),

      ...sp(2),
      separator(),

      // Section 5
      h1("5. Migration Implications"),
      h2("5.1 Scope"),
      p("The system is pre-production with seed data only. No live data migration constraints apply. All changes can be implemented as clean schema migrations."),

      ...sp(),
      h2("5.2 Breaking Changes by Entity"),

      makeTable(
        ["Entity", "Breaking Change", "Action Required"],
        [
          ["Client (current)", "Split into Person + LegalEntity + ClientRecord", "New models, new tables, remove Client table"],
          ["Business", "Change FK from client_id to legal_entity_id", "Schema migration"],
          ["VatReport", "Change client_id to client_record_id, add unique constraint", "Schema migration"],
          ["AnnualReport", "Change client_id to client_record_id, add unique (client_record_id, tax_year)", "Schema migration"],
          ["TaxDeadline", "Change client_id to client_record_id, add unique constraint, add canceled state", "Schema migration"],
          ["Binder", "Change client_id to client_record_id, add archived_in_office state", "Schema migration"],
          ["Reminder", "Change client_id to client_record_id, fix CUSTOM to not require business_id", "Schema migration + service fix"],
          ["Document", "Change client_id to client_record_id", "Schema migration"],
          ["All routes", "Update path params and body fields from client_id to client_record_id", "API layer update"],
        ],
        [1800, 3400, 4160]
      ),

      ...sp(2),
      h2("5.3 Recommended Execution Order"),
      p("Layers must be built bottom-up. Do not start on Layer 2 until Layer 1 is complete and tested."),
      ...sp(),
      bullet("Layer 1 — New models: Person, LegalEntity, ClientRecord, PersonLegalEntityLink"),
      bullet("Layer 1 — Migrate Business FK to legal_entity_id"),
      bullet("Layer 1 — Migrate all workflow entities to client_record_id"),
      bullet("Layer 1 — Update all services and routes"),
      bullet("Layer 2 — Add unique constraints on obligation identity keys"),
      bullet("Layer 2 — Fix sync logic to use domain keys instead of date ranges"),
      bullet("Layer 2 — Add entity_type change guard (ADVISOR-only + drift handling)"),
      bullet("Layer 3 — Add missing terminal states to TaxDeadline, VatReport, AnnualReport, Binder"),
      bullet("Layer 3 — Implement ClientRecord closure lifecycle policy"),
      bullet("Layer 3 — Add cascade Reminder cancellation on ClientRecord close"),
      bullet("Layer 4 — Fix RBAC: entity_type to ADVISOR-only"),
      bullet("Layer 4 — Fix CUSTOM Reminder to support client_record_id without mandatory business_id"),
      bullet("Layer 4 — Review UX/RBAC gaps after the new model is stable"),
      bullet("Future — Introduce Obligation entity as shared identity anchor"),

      ...sp(2),
      h2("5.4 Decisions Not Yet Made"),
      p("The following items are deferred and require a separate decision before implementation:"),
      ...sp(),
      bullet("RBAC model for Layer 4 and beyond: does the system need roles beyond ADVISOR / SECRETARY?"),
      bullet("Document-to-VatReport linkage: is direct association needed, or is client_record_id + period sufficient?"),
      bullet("Obligation entity: implement now alongside Layer 2, or defer to a future iteration?"),
      bullet("Person national_id: Israeli ID only, or multi-country from the start?"),

      ...sp(2),
      separator(),

      new Paragraph({
        children: [new TextRun({ text: "End of Domain Decision Document v1.0", size: 20, font: "Arial", color: "808080", italics: true })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 0 }
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/claude/domain_decision_doc.docx", buffer);
  console.log("Done.");
});
