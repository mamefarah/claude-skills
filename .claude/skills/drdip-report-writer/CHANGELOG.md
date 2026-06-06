# CHANGELOG — drdip-report-writer

## v1.1 — 2026-06-06

### Main Purpose

Upgrade the skill to generate full professional standard regional management reports: the Monthly Regional Progress Report, the Quarterly Regional Progress Report, and the Annual Regional Progress Report. These are the primary accountability and management deliverables for the Somali Region DRDIP-II PCU. The skill remains a professional report generator and does not generate travel audits, per diem audit logs, or compliance workbooks unless explicitly requested.

### Files Created (9 new files)

```
.claude/skills/drdip-report-writer/
└── resources/
    ├── report_templates/
    │   ├── monthly_regional_progress_report_template.md
    │   ├── quarterly_regional_progress_report_template.md
    │   ├── annual_regional_progress_report_template.md
    │   ├── dqa_checklist_template.md
    │   └── non_compliance_corrective_action_tracker_template.md
    ├── reference_tables/
    │   └── location_master_table.md
    └── optional_annexes/
        ├── compliance_tracker_annex.md
        ├── financial_summary_annex.md
        └── safeguards_grm_summary_annex.md
```

### Files Updated

- `SKILL.md` — version bumped to 1.1, description updated, blocking rule updated, report types table expanded to 12 types, quarterly routing rule added, template file map expanded, component inclusion rule updated, Part 7.10-7.13 added
- `CHANGELOG.md` — this entry

### New Report Types Added

1. Monthly Regional Progress Report (13 sections) — with AWPB-linked progress table, financial performance, beneficiary/GESI breakdown, safeguards/GRM summary, action matrix
2. Quarterly Regional Progress Report (19 sections) — with full AWPB tracking, procurement summary, GESI performance, data quality section, action matrix
3. Annual Regional Progress Report (19 sections) — with results framework table, GESI analysis, strategic recommendations, lessons learned, next EFY priorities

### New Capabilities

- Generate full monthly DRDIP-II regional report
- Generate full quarterly DRDIP-II regional report
- Generate full annual DRDIP-II regional report
- Generate blank monthly, quarterly, or annual report template
- Convert raw component data into a full report
- Prepare executive summary and action matrix
- Create missing information list
- Apply DQA checklist before report submission
- Attach NC-CAT tracker as optional annex when requested

### Design Decisions

- Three new standard regional report templates cover 13-19 sections each. All include cover page, executive summary, four-component progress sections, financial performance, beneficiary/GESI breakdown, safeguards/GRM summary, action matrix, and optional annexes.
- Monthly template includes AWPB-linked progress table (10 columns) in Section 5, linking monthly achievements to approved Annual Work Plan and Budget activities.
- Quarterly routing rule: "quarterly regional report", "FPCU quarterly report", "regional quarterly progress report", or "full quarterly report" routes to the new 19-section template. Smaller activity-level quarterly updates route to the v1.0 template.
- Optional Annex Rule (Part 7.13): travel audit logs, per diem climate-tier tables, transport receipt logs, workbook-style trackers, formula-heavy sections, and detailed compliance columns are never mandatory sections. Attach as optional annexes on explicit request only.
- DQA checklist and NC-CAT tracker are provided as support tools only.
- All three optional annex shells are blank with usage notes — include only when explicitly requested.
- Component inclusion rule updated: all four components are required for monthly, quarterly regional, and annual reports.
- location_master_table.md provides the canonical reference for all eight official location names and variant spelling maps.
- Confidentiality: SEA/SH case details are never included in main report sections. Aggregate counts only.

### Future Upgrade Notes for v1.2

- Consider adding indicator tracking templates pre-loaded with DRDIP-II PDO and intermediate indicators.
- Consider adding woreda-level sub-templates for the annual report annexes.
- Consider adding an Amharic or Somali output language option.
- Consider splitting SKILL.md into a core file and per-report-type instruction files if context limits become a concern with large raw data inputs.
- Consider adding a glossary file for DRDIP-II terminology, acronyms, and safeguards instrument definitions.

---

## v1.0 — 2026-06-05

### Files Created

```
.claude/skills/drdip-report-writer/
├── SKILL.md
├── CHANGELOG.md
└── resources/
    ├── report_templates/
    │   ├── field_mission_report_template.md
    │   ├── training_report_template.md
    │   ├── quarterly_progress_report_template.md
    │   ├── supervision_report_template.md
    │   ├── safeguards_report_template.md
    │   ├── m_and_e_report_template.md
    │   ├── committee_meeting_report_template.md
    │   └── action_matrix_template.md
    └── checklists/
        ├── report_quality_checklist.md
        ├── missing_information_checklist.md
        ├── drdip_component_classification.md
        └── findings_recommendations_rules.md
```

### Main Purpose

Convert raw DRDIP-II notes, field observations, activity summaries, training data, meeting notes, supervision findings, and monitoring updates into professional, copy-ready reports. Supports nine report types for the Somali Region Development Response to Displacement Impacts Project II (DRDIP-II), a World Bank-funded program implemented by the Somali Regional State Bureau of Agriculture, DRDIP-II Regional Project Coordination Unit.

### Supported Report Types

1. Field mission report
2. Training report
3. Quarterly progress report
4. Supervision report
5. Safeguards report
6. M&E report
7. Steering committee meeting report
8. Technical committee meeting report
9. Action matrix report

### Design Decisions

- Markdown only. No Python scripts in v1.0.
- Single SKILL.md with ten PARTS covers all nine report types.
- Eight report templates provide blank pre-structured drafts per type.
- Four checklist files support report authors outside of Claude sessions.
- Component inclusion rule: all four components required only for quarterly progress reports. Other report types include only covered components.
- Blocking rule: skill only asks follow-up questions when report type, core activity, or objective is missing. All other missing fields use [MISSING] placeholders.

### Future Upgrade Notes for v1.1

- Consider adding a Python script to validate planned vs actual arithmetic in progress tables.
- Consider adding indicator tracking templates pre-loaded with DRDIP-II PDO and intermediate indicators.
- Consider splitting SKILL.md into a core file and per-report-type instruction files if context limits become a concern with large raw notes.
- Consider adding an Amharic or Somali output language option.
- Consider adding a glossary file for DRDIP-II terminology, acronyms, and safeguards instrument definitions.
