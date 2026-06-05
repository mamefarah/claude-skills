# CHANGELOG — drdip-report-writer

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
