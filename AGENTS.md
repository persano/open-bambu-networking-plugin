# Agent rules

## Changelog format: Keep a Changelog subsections

Both `CHANGELOG.md` and `docs/ORCACLOUD_CHANGELOG.md` group every version
section's bullets under level-3 category headings, in this order, skipping
categories with no bullets:

```
## 0.2.48 - 2026-11-08

### Added
- bullet

### Changed
- bullet

### Fixed
- bullet
```

Only `### Added`, `### Changed`, `### Fixed`, `### Removed` are allowed as
category headings. Bullets stay verbatim (never reword or re-wrap them while
reformatting). Version headings stay level 2 (`##`), always with one blank
line before and after.

## OrcaCloud changelog must not repeat the version heading

OrcaCloud renders its own version/date chip above the changelog, so a
`## x.y.z - date` line at the top of the payload reads as a duplicate.
`publish-orcacloud.yml` strips level-2 headings (`sed '/^## /d'`) from the
changelog right before upload; level-3 subsections pass through (`^## ` does
not match `### `). Keep this strip when editing the workflow. The GitHub
release body itself still carries the full section including its heading —
only the OrcaCloud payload is stripped.

## Release notes must carry the changelog

A GitHub release body must contain the verbatim matching section from
`docs/ORCACLOUD_CHANGELOG.md` (fallback source `CHANGELOG.md`), so the
publish workflow and humans read the same words.
