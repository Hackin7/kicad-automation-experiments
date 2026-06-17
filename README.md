# KiCad Automation Experiments

This repository is set up to test GitHub Actions automation for KiCad hardware projects.

## GitHub Actions

Two hardware workflows are configured:

- **Hardware CI** (`.github/workflows/hardware.yml`) runs on hardware and CI config changes. It runs KiBot ERC/DRC checks, generates schematic and PCB PDFs, BOMs, fabrication packages, JLCPCB outputs, 3D model artifacts, a GitHub Actions summary, and a GitHub Pages review site.
- **Hardware PR Visual Diff** (`.github/workflows/hardware-pr-diff.yml`) runs on pull requests. It compares KiCad schematic and PCB renders against the base branch and comments on the PR with links to the visual diff artifacts.

The board registry lives at `.github/hardware/projects.json`. Add a board under `hardware/`, then add an entry to that registry so both workflows include it.

Generated CI files are uploaded as Actions artifacts. Source KiCad files stay under `hardware/`; CI helper scripts, site templates, and registry data stay under `.github/hardware/`.
