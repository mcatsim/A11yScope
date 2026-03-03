# Rename: A11yScope → A11yScope — Design Document

**Date:** 2026-03-02
**Status:** Approved

## Brand Identity

| Element | Old Value | New Value |
|---------|-----------|-----------|
| Display name | A11yScope | A11yScope |
| Python package | a11yscope | a11yscope |
| CLI commands | a11yscope, a11yscope-web | a11yscope, a11yscope-web |
| Env var prefix | A11YSCOPE_ | A11YSCOPE_ |
| GitHub repo | mcatsim/A11yScope | mcatsim/A11yScope |
| Docker service | a11yscope | a11yscope |
| Docker volume | a11yscope-data | a11yscope-data |
| DB default path | data/a11yscope.db | data/a11yscope.db |

## Scope

111 files across Python source, tests, docs, config, CI, and frontend.
Zero behavior changes — purely mechanical rename.
