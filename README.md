# KiCad Automation Experiments

This repository is set up to test GitHub Actions automation for KiCad hardware projects.

## GitHub Actions

Two hardware workflows are configured:

- **Hardware CI** (`.github/workflows/hardware.yml`) runs on hardware and CI config changes.
- **Hardware PR Visual Diff** (`.github/workflows/hardware-pr-diff.yml`) runs on pull requests.

## Checks And Outputs

- **ERC**: schematic electrical rules.
- **DRC**: PCB design rules.
- **Zone fill check**: verifies filled copper zones.
- **Schematic PDF**: review copy of the schematic.
- **PCB layer PDFs**: review plots for board layers.
- **BOMs**: generic and JLCPCB CSV outputs.
- **Fabrication files**: Gerbers, drills, and zip packages.
- **3D model**: browser-viewable board model when export works.
- **GitHub Pages site**: per-board review pages.
- **PR visual diff**: schematic and PCB image diffs against the base branch.
- **PR bot comment**: links to visual diff artifacts.

## Repo Layout

- `.github/workflows/`: GitHub Actions workflows.
- `.github/hardware/projects.json`: board registry used by CI.
- `.github/hardware/site/`: GitHub Pages review-site template and styles.
- `.github/hardware/3d/`: 3D conversion helper scripts.
- `.github/hardware/report_summary.py`: ERC/DRC summary formatter.
- `hardware/`: KiCad project source files.
- `docs/`: project notes and documentation.

The board registry lives at `.github/hardware/projects.json`. Add a board under `hardware/`, then add an entry to that registry so both workflows include it.

## Notes

JLCPCB BoM is working (entry using JLCPCB Plugin into PCB design)

## Future TODOs

- Allow Preview of PRs on Github Pages -> board + diff ui (a better diff ui would be nice)
- Test of effectiveness on a private repo (PR actions etc.)
  - if there's a local/ web app to download Github CI results and view them for private repos
- Improve Website UI (feels very Vibe Coded)
  - Integrate the various components more cohesively when possible


Generated CI files are uploaded as Actions artifacts. Source KiCad files stay under `hardware/`; CI helper scripts, site templates, and registry data stay under `.github/hardware/`.
