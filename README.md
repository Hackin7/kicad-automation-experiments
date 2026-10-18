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

- `actions/discover`, `actions/build`, and `actions/viewer`: reusable KiCad review actions. Hardware CI calls them at `Hackin7/kicad-automation-experiments/actions/<name>@main`, the same way another repository would.
- `.github/kicad-viewer.yml`: optional project names, slugs, and production paths for this repo.
- `.github/workflows/`: GitHub Actions workflows.
- `.github/hardware/projects.json`: board registry still used by the pull request diff workflow.
- `.github/hardware/report_summary.py`: ERC/DRC summary formatter.
- `hardware/`: KiCad project source files.
- `docs/`: project notes and documentation.

Boards are discovered from committed `.kicad_pro` files. `.github/kicad-viewer.yml` pins the names and slugs used by the published review site. The pull request diff workflow still reads `.github/hardware/projects.json`.

## Use in another repository

```yaml
jobs:
  discover:
    runs-on: ubuntu-latest
    outputs:
      projects: ${{ steps.discover.outputs.projects }}
      matrix: ${{ steps.discover.outputs.matrix }}
    steps:
      - uses: actions/checkout@v6
      - id: discover
        uses: Hackin7/kicad-automation-experiments/actions/discover@main
  build:
    needs: discover
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.discover.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v6
      - uses: Hackin7/kicad-automation-experiments/actions/build@main
        with:
          project: ${{ toJson(matrix) }}
  viewer:
    needs: [discover, build]
    if: ${{ always() && needs.discover.result == 'success' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v6
      - uses: Hackin7/kicad-automation-experiments/actions/viewer@main
        with:
          projects: ${{ needs.discover.outputs.projects }}
          deploy: ${{ github.ref == 'refs/heads/main' }}
```

The build job is optional. Without it, the viewer still publishes KiCanvas and any committed production files. An optional `.github/kicad-viewer.yml` can set `name`, `slug`, `production`, `kibot`, and `enabled` for each project path. `{dir}` and `{basename}` placeholders work in production and KiBot paths.

## Notes

JLCPCB BoM is working (entry using JLCPCB Plugin into PCB design)

## Future TODOs

- [x] Allow Preview of PRs on Github Pages -> board + diff ui (a better diff ui would be nice)
  - [ ] Improve the diff such that it syncs up between commits
  - [ ] iBOM cannot be displayed in the web browser on PR preview
- Test of effectiveness on a private repo (PR actions etc.)
  - if there's a local/ web app to download Github CI results and view them for private repos
- Improve Website UI (feels very Vibe Coded)
  - Integrate the various components more cohesively when possible
  - Refactor the codebase to be nicer for humans


Generated CI files are uploaded as Actions artifacts and published on the review site. Source KiCad files stay under `hardware/`. The reusable actions live under `actions/`.
