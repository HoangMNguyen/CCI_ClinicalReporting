# New automations build on base reports; existing per-study modules stay

New automations get their data from a base report: a saved setting versioned in the repo next to the automation's code, applied to the Corelisting export through the Qt-free Clinical Reporting core. The automation then adds its own statistics, sheets and formatting. The existing DSMB, Enrollment Log and AE & DLT per-study modules keep their hand-written pandas code and are not migrated. Migrating them would mean proving each study's DSMB and safety workbooks identical for no change in what users get. New automations, meanwhile, reuse a report definition the team already maintains instead of copying per-study code.

## Consequences

- Two ways of building a report coexist on purpose; a per-study module is not a candidate for conversion just because it predates base reports.
- An automation's output changes only through a reviewed commit, because its saved setting is versioned with its code rather than read from the team's shared settings folder.
- Run through the API, a base report must produce a workbook byte-identical to the desktop export for the same inputs (except its creation timestamp), so the decisions on that path that today live only in the desktop window move into the core first.
