# DESIGN.md — token contract (human source of truth)

The site's design tokens are single-sourced. `app/tokens.css` is the rendered
CSS-custom-property form; this document is the human contract. Components
resolve **every** color, space, radius, and border from a named token — no
hard-coded literals (DS-01, DS-07, DS-10).

## Color (dark, restrained, semantic)
| Token | Value | Use |
|---|---|---|
| `--canvas` | `#0A0B0D` | page background |
| `--surface` / `--surface-2` | `#121417` / `#181B1F` | panels, cards, code/trace blocks |
| `--border` | `#1E2227` | hairline borders |
| `--text` / `--text-muted` / `--text-faint` | `#F5F7FA` / `#8A8F98` / `#5A606B` | body / secondary / decorative-disabled only |
| `--proven` (`--signal`) | `#34E1A0` | **verification / system-correct states ONLY** (~12.5:1 on canvas) |
| `--pending` | `#E2B340` | awaiting-evidence states |
| `--error` | `#E5484D` | **genuine runtime errors ONLY** |

**Accent discipline:** `--proven` is reserved for proved requirements, satisfied
gates, and confirmed evidence — never decoration. On the homepage it appears at
only two beats (the gate-hold and the completed evidence record).

## Type
- `--font-sans` (Geist Sans, self-hosted) for display/body; weights 300–600.
- `--font-mono` (Geist Mono) for **machine artifacts only** — requirement IDs,
  evidence records, hashes, gate verdicts, code, trace spans (rendered on
  `[data-artifact]` nodes).

## Layout
Spacing scale (`--space-*`), radius (`--radius-*`), hairline border, and
`--container-max` (1180px). Components compose layout exclusively from these.
