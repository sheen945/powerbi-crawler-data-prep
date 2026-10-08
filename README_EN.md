# powerbi-crawler-data-prep

> An Agent Skill that pipelines messy, crawler-harvested multi-source data (JSON/CSV/Excel mixed) into a local Power BI Desktop deliverable: M cleaning flows → star schema → multi-page report → **`.pbit` template delivery** → live-model verification via Power BI MCP.

## Introduction

This is a WorkBuddy / Claude Code Agent Skill built for one specific pipeline: **web-scraped data → local Power BI Desktop**. The crawler drops new JSON/CSV/Excel files into the same folder every day; the data is always dirty (inconsistent column names, numbers stored as text, multiple spellings of the same entity, duplicate scrapes); and all the user wants is: run the crawler, drop the files, hit refresh, and look at a multi-page dashboard. This skill engineers everything in between — Power Query M cleaning, star-schema modeling, PBIP project management, final `.pbit` template export, and live-model verification against a running Power BI Desktop instance (refresh / row counts / reconciliation / per-page screenshots) — with reusable templates, hard-won pitfall lists, and automation scripts for every step.

**Trigger scenarios**: getting crawler data into Power BI, multi-format merging, daily / per-match-day incremental refresh, basketball/match data cleaning, CC-index / injury / starting-lineup visualization, star schema / dimensional modeling / measures / calculated columns, "show me in Power BI" / "open Power BI for me", building a pbip / Power BI project / template / pbit, exporting pbit, Power BI MCP, writing Power Query M code.

## Features

- **Three unified entry points**: JSON → `Json.Document`, CSV → `Csv.Document`, Excel → `Excel.Workbook` — one entry query per format, column structures aligned, then combined vertically with `Table.Combine`
- **Daily incremental pipeline**: built on the `Folder.Files` connector — new crawler files dropped into the same folder are automatically picked up and merged; the only user actions are "run crawler → drop files → click refresh"
- **Crawler-specific cleaning patterns**: one-step batch renaming via mapping table (`Table.RenameColumns`), team/player alias tables for name normalization (e.g. "Lakers" / "Los Angeles Lakers" / "LAL" → one canonical name), text-to-number conversion with `Number.FromText` + `try...otherwise null`, and missing-key rows flagged with a marker column instead of silently deleted
- **Explicit deduplication**: duplicate scrapes are the norm — dedupe on an explicit key (match date + player, or your business key) to prevent double imports
- **Star-schema modeling rules**: fact tables hold "what happened", dimensions hold "attributes" and are derived from the same fact pipeline (refresh keeps them in sync); only fact→dimension relationships are allowed; calculated columns carry static attributes only — all aggregation goes through measures (with format strings, display folders, and Chinese descriptions); ships with 18 measure templates and dashboard layout coordinates
- **M language engineering standards**: 8 high-frequency core rules (human-readable step names, early type conversion, batch renames, early column/row pruning, step-by-step debugging, explicit error handling…) plus a full anti-pattern list
- **`.pbit` as the sole delivery format** (rule set on 2026-10-07): PBIP is only the intermediate engineering carrier — the final artifact **must** be exported via Desktop's File → Export → Power BI template; the full export flow (a 9-step recipe) is automatable except for the parameter dialog (1–2 manual actions)
- **Live-model verification loop**: after producing a PBIP, always run offline validation (`pbip_load_project` → `pbip_validate` → `pbir_validate_report`) → open in Desktop → TOM refresh → DAX row-count/reconciliation checks → per-page screenshot evidence; verify once more after exporting the PBIT
- **Battle-tested pitfall table**: 12 rows of "don't do this / why / do this instead" (hand-crafting PBIT, `pbi-tools compile`, `mouse_event` on the backstage panel, eyeballing coordinates from screenshots, `netstat` for the AS port… every row backed by a real incident)
- **Bundled MCP server source**: the `mcp/` directory contains the full Power BI MCP server (82 tools) with 3 local patches that close the "live local Desktop verification" loop

## How It Works & Tech Stack

### Four Iron Rules (verified premises of this project's environment)

1. **Query folding does not exist** — flat files (JSON/CSV/Excel) have no query engine; performance work reduces to "prune columns early, filter rows early"
2. **Crawler data is always dirty** — not a single cleaning step can be skipped
3. **Daily increment = the folder connector** — `Folder.Files` merges everything automatically
4. **The dedup key must be explicitly defined** — otherwise re-scrapes silently double your data

### Five-Step Standard Workflow

1. **Unified entry**: one entry query per format, aligned column structures
2. **Merge sources**: align names/order/types, then `Table.Combine`
3. **Crawler-specific cleaning**: field mapping → name normalization → text-to-number → missing-value flagging (fixed order)
4. **Daily incremental pipeline**: `Folder.Files` lists all files → route by extension → merge → dedupe
5. **Verify**: the five-item checklist — syntax, data, types, nulls, row counts

### Six-Step Delivery Chain (fixed order — no skipping, no reordering)

```
① Generate the PBIP project (Python generator; one column list drives both
  the M code and the TMDL column definitions)
② Offline validation (pbip_load_project → pbip_validate → pbir_validate_report,
  all green before continuing)
③ Live verification (open Desktop → TOM refresh → DAX row counts/reconciliation)
④ Export the PBIT (Desktop File → Export → Power BI template; 9-step automated recipe)
⑤ Acceptance (opening the file for real pops the parameter dialog named after
  the template — that's the hard proof)
⑥ Package the delivery (a zip: pbit + PBIP project + raw data + screenshots +
  prompts + notes, stating the minimum required Desktop version)
```

⛔ **Hard rule: never hand-craft a PBIT.** It has hit the wall three times (including a full rebuild against the real internal structure with `lineageTag` completed) — Desktop still reports "file is corrupted or the version is not recognized". See the postmortem in `references/pbit-export.md`.

### Tech Stack

- **Power Query M**: the cleaning/transformation layer (methodology partially derived from [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development), trimmed for local Desktop + flat-file scenarios)
- **PBIP / TMDL / PBIR**: Power BI's project formats — plain text, readable and writable offline via MCP (iron rule: TMDL files must be UTF-8 **without BOM**)
- **Power BI MCP** (`mcp/powerbi-mcp/`): a Python MCP server with 82 tools; TOM/ADOMD live-model connections, Desktop Bridge named-pipe hot reload, and per-page screenshots
- **Python scripts**: the PBIP generator, the TOM refresh script (`RequestRefresh(Full)` + `SaveChanges`), and a ctypes PrintWindow fallback for window screenshots
- **Local Desktop only**: no Fabric cloud; Azure credentials are optional

## Installation & Usage

### Install the skill

Copy this repository's directory into your skills folder, keeping the folder name `powerbi-crawler-data-prep`:

- WorkBuddy / CodeBuddy: `~/.workbuddy/skills/powerbi-crawler-data-prep/`
- Claude Code: `~/.claude/skills/powerbi-crawler-data-prep/`

Restart the session and the trigger phrases will match automatically (e.g. "get crawler data into Power BI", "export pbit", "write Power Query M code").

### Wire up the bundled Power BI MCP (optional, for live verification)

The `mcp/` directory holds the bundled **Power BI MCP server source** (upstream: [sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp); this copy carries 3 local patches: bridge `args` contract, a concurrent-write lock, and backups landing in temp). Add this to the `mcpServers` section of your MCP config:

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "<path to your python interpreter>",
      "args": ["<repo path>/mcp/powerbi-mcp/src/server.py"],
      "env": {
        "PYTHONPATH": "<repo path>/mcp/powerbi-mcp/src",
        "ADOMD_DLL_PATH": "<directory holding the ADOMD/TOM DLLs>",
        "TOM_DLL_PATH": "<directory holding the ADOMD/TOM DLLs>"
      }
    }
  }
}
```

Dependencies:

- Offline-analysis only (PBIP/TMDL/PBIR editing, BPA audits, DAX linting) → `pip install -r requirements-core.txt`, **no .NET required**
- Live Power BI Desktop capabilities (refresh, DAX execution, bridge screenshots) → `pip install -r requirements.txt`, which needs `pythonnet` + `pyadomd`
- The ADOMD/TOM .NET assemblies (~97 MB, Microsoft copyrighted) are not redistributed with this repo. Fetch `Microsoft.AnalysisServices.AdomdClient` and `Microsoft.AnalysisServices.Tabular` from NuGet, unzip the packages, and copy the `lib/` DLLs into the directory above

## Project Structure

```
powerbi-crawler-data-prep/
├── SKILL.md                                # Skill definition (triggers + full methodology)
├── README.md                               # 中文版说明
├── README_EN.md                            # This file
├── references/                             # Reference docs, indexed by "which step am I on"
│   ├── pbit-export.md                      # ⭐ .pbit internals / export automation / acceptance
│   ├── pbip-delivery.md                    # PBIP structure / TMDL hard rules / no-BOM / offline checks
│   ├── powerbi-mcp.md                      # Live verification: MCP tool cheatsheet / chain / local patches
│   ├── m-core.md                           # Full M language standards
│   ├── sources-and-pipeline.md             # Three entry templates + Folder.Files incremental pipeline
│   ├── crawler-cleaning-patterns.md        # Field mapping / name normalization / text→number / dedup
│   └── star-schema-and-dax.md              # Star schema & DAX (18 measure templates + layout coords)
└── mcp/
    ├── README.md                           # How to wire up the bundled MCP
    └── powerbi-mcp/                        # Power BI MCP server source (82 tools)
        ├── src/                            # server.py / desktop_bridge.py /
        │                                   # powerbi_pbip_connector.py (local patches) /
        │                                   # powerbi_tom_connector.py / security/ ...
        ├── config/policies.yaml            # Security policies
        ├── docs/                           # ARCHITECTURE / TESTING / TOOLS
        ├── tests/                          # 25 test files
        ├── requirements-core.txt           # Cross-platform deps (no .NET)
        └── requirements.txt                # Full Windows deps (pythonnet / pyadomd)
```

## Notes & Caveats

- **Local Desktop only**: Fabric cloud scenarios are out of scope; cloud-verification content has been deliberately trimmed
- **The deliverable is a `.pbit`** — not a `.pbix`, not the PBIP folder. PBIP is only the intermediate carrier
- **Always deliver as a zip**: pbit + PBIP project + raw data + screenshots + prompts + notes, and state the minimum required Desktop version. Sending a lone pbit file leaves the recipient with no fallback when it won't open
- **Compatibility levels only go up, never down** (officially `irreversible`) — do not attempt to produce a "downward-compatible" pbit
- **The MCP has no refresh tool**: refresh requires a TOM script (`RequestRefresh(Full)` + `SaveChanges`); a `COUNTROWS` returning null means the model was never refreshed, not that the model is broken
- **The MCP patches are lost on upgrade**: the 3 local patches (bridge `args` contract, concurrent-write lock, backups to temp) live in `mcp/powerbi-mcp/src/` and must be reapplied after pulling upstream
- **Desktop automation details**: never resize the Desktop window after opening a model (WebView child geometry doesn't follow); use `SendInput` rather than `mouse_event` for the backstage panel; compute coordinates via dark-pixel scanning + `EnumChildWindows`, never by eyeballing screenshots
- The `mcp/` source has passed a secrets audit — no real credentials; logs, caches, and database files are not committed

## License

**GPL-3.0**

The Power Query M methodology portion of this skill is derived from the power-query skill in [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development) (GPL-3.0), trimmed for local Desktop + flat-file scenarios (query folding, Fabric cloud verification and other inapplicable content removed); the crawler data-cleaning patterns are original additions. `mcp/powerbi-mcp/` is modified from the open-source project [sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp).

## Author

[sheen945](https://github.com/sheen945)
