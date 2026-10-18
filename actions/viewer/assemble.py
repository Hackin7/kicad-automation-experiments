#!/usr/bin/env python3
"""Assemble the hardware review site from discovered projects and build artifacts."""

import argparse
import html
import json
import os
import shutil
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", default="")
    parser.add_argument("--root", default=".")
    parser.add_argument("--artifacts", default="artifacts")
    parser.add_argument("--templates", default="")
    parser.add_argument("--out", default="site")
    parser.add_argument("--title", default="")
    parser.add_argument("--summary", action="store_true")
    return parser.parse_args()


def load_projects(raw):
    if not raw:
        raw = os.environ.get("PROJECTS_JSON", "")
    if not raw:
        raise SystemExit("No projects JSON was provided")
    projects = json.loads(raw)
    if isinstance(projects, dict) and "include" in projects:
        projects = projects["include"]
    return projects


def copy_tree(source, destination):
    if not source.exists():
        return False
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return True


def copy_file(source, destination):
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def file_type(path):
    suffix = path.suffix.lower().lstrip(".")
    return {"htm": "HTML", "html": "HTML", "csv": "CSV", "zip": "ZIP", "pdf": "PDF", "wrl": "WRL", "vrml": "WRL", "step": "STEP", "stp": "STEP", "gbr": "GBR"}.get(suffix, suffix.upper() or "FILE")


def classify(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    if "ibom" in name and suffix in {".html", ".htm"}:
        return "downloads"
    if suffix == ".pdf":
        return "pdfs"
    if suffix in {".csv", ".zip", ".gbr", ".gerber", ".step", ".stp", ".wrl", ".vrml", ".html", ".htm"}:
        return "downloads"
    return ""


def label_for(path):
    stem = path.stem.replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in stem.split())


def collect_links(base, folder):
    downloads = []
    pdfs = []
    if not folder.exists():
        return downloads, pdfs
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or "shapes3D" in path.parts:
            continue
        group = classify(path)
        if not group:
            continue
        item = {
            "label": label_for(path),
            "href": path.relative_to(base).as_posix(),
            "type": file_type(path),
        }
        (pdfs if group == "pdfs" else downloads).append(item)
    return downloads, pdfs


def find_html(folder, kind):
    if not folder.exists():
        return None
    matches = [
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".htm"} and kind in path.name.lower()
    ]
    return sorted(matches)[0] if matches else None


def write_fallback(path, title):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(
        "<!doctype html><title>{0} unavailable</title><h1>{0} unavailable</h1><p>No {0} report was produced for this run.</p>".format(title),
        encoding="utf-8",
    )


def read_status(artifact_dir):
    status_path = artifact_dir / "status.json"
    if not status_path.is_file():
        return {"checks": "unknown", "outputs": "unknown", "models": "unknown"}
    data = json.loads(status_path.read_text(encoding="utf-8"))
    return {
        "checks": data.get("checks", "unknown"),
        "outputs": data.get("outputs", "unknown"),
        "models": data.get("models", "unknown"),
    }


def worst(values):
    normalized = [str(value or "unknown").lower() for value in values]
    if any(value in {"failure", "failed", "cancelled"} for value in normalized):
        return "failure"
    if any(value == "success" for value in normalized):
        return "success"
    if any(value == "skipped" for value in normalized):
        return "skipped"
    return "unknown"


def pill(state, text):
    return '<span class="pill" data-state="{0}">{1}</span>'.format(state, text)


def board_card(project):
    return """
                    <a class="board-card" href="projects/{slug}/">
                      <span class="board-name">{name}</span>
                      <span class="board-path">{directory}</span>
                      <span class="board-meta">{board}</span>
                    </a>""".format(
        slug=html.escape(project["slug"]),
        name=html.escape(project["name"]),
        directory=html.escape(project.get("dir") or "."),
        board=html.escape(project.get("board") or project.get("project") or ""),
    )


def write_index(out, templates, title, projects, statuses, run_url, sha):
    checks = worst(status["checks"] for status in statuses)
    outputs = worst(status["outputs"] for status in statuses)
    models = worst(status["models"] for status in statuses)
    cards = "\n".join(board_card(project) for project in projects) or '<div class="empty-state"><p>No KiCad projects were discovered.</p></div>'
    html = (templates / "boards-index.html").read_text(encoding="utf-8")
    replacements = {
        "__TITLE__": title,
        "__RUN_URL__": run_url,
        "__SHA__": sha[:12],
        "__CHECKS_STATE__": checks,
        "__CHECKS_TEXT__": "ERC / DRC " + checks,
        "__OUTPUTS_STATE__": outputs,
        "__OUTPUTS_TEXT__": "Outputs " + outputs,
        "__MODELS_STATE__": models,
        "__MODELS_TEXT__": "3D " + models,
        "__BOARDS__": cards,
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "boards.json").write_text(json.dumps([
        {
            "name": project["name"],
            "slug": project["slug"],
            "status": status,
        }
        for project, status in zip(projects, statuses)
    ], indent=2) + "\n", encoding="utf-8")


def write_summary(out, page_url):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    boards = json.loads((out / "boards.json").read_text(encoding="utf-8"))
    base = page_url.rstrip("/") if page_url else ""
    lines = ["## Hardware review", ""]
    if base:
        lines.append("[Open review site]({0})".format(base))
        lines.append("")
    lines.extend(["| Board | Review page | ERC / DRC | Outputs | 3D |", "| --- | --- | --- | --- | --- |"])
    for board in boards:
        status = board["status"]
        if base:
            link = "[Open]({0}/projects/{1}/)".format(base, board["slug"])
        else:
            link = "Not published"
        lines.append("| {name} | {link} | `{checks}` | `{outputs}` | `{models}` |".format(
            name=board["name"],
            link=link,
            checks=status.get("checks", "unknown"),
            outputs=status.get("outputs", "unknown"),
            models=status.get("models", "unknown"),
        ))
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def assemble(args):
    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    templates = Path(args.templates) if args.templates else Path(__file__).resolve().parent / "site"
    artifacts = Path(args.artifacts)
    if not artifacts.is_absolute():
        artifacts = Path.cwd() / artifacts
    projects = load_projects(args.projects)
    title = args.title or os.environ.get("GITHUB_REPOSITORY", "Hardware Boards").split("/")[-1]
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_url = "{0}/{1}/actions/runs/{2}".format(server, repository, run_id) if repository and run_id else ""

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in ("style.css", "theme.js"):
        shutil.copy2(templates / name, out / name)
    preview = out / "preview"
    preview.mkdir()
    shutil.copy2(templates / "pr-preview.html", preview / "index.html")

    statuses = []
    for project in projects:
        slug = project["slug"]
        project_site = out / "projects" / slug
        for folder in ("reports", "outputs", "kicad", "model", "files"):
            (project_site / folder).mkdir(parents=True, exist_ok=True)
        directory = project.get("dir") or ""
        source_dir = root / directory
        for key in ("project", "schematic", "board"):
            filename = project.get(key) or ""
            if filename:
                copy_file(source_dir / filename, project_site / "kicad" / filename)

        artifact_dir = artifacts / "{0}-kicad-build".format(slug)
        copy_tree(artifact_dir / "reports", project_site / "reports")
        copy_tree(artifact_dir / "outputs", project_site / "outputs")
        copy_tree(artifact_dir / "model", project_site / "model")
        for production in project.get("production") or []:
            copy_tree(root / production, project_site / "files" / Path(production).name)

        downloads, pdfs = [], []
        for folder in ("outputs", "files", "model"):
            extra_downloads, extra_pdfs = collect_links(project_site, project_site / folder)
            downloads.extend(extra_downloads)
            pdfs.extend(extra_pdfs)

        basename = project.get("basename") or slug
        erc = find_html(project_site / "reports", "erc")
        drc = find_html(project_site / "reports", "drc")
        if erc is None:
            erc = project_site / "reports" / "{0}-erc.html".format(basename)
            write_fallback(erc, "ERC report")
        if drc is None:
            drc = project_site / "reports" / "{0}-drc.html".format(basename)
            write_fallback(drc, "DRC report")
        status = read_status(artifact_dir)
        statuses.append(status)
        info = {
            "runUrl": run_url,
            "sha": sha,
            "checksResult": status["checks"],
            "outputsResult": status["outputs"],
            "modelsResult": status["models"],
            "projectName": project.get("name") or slug,
            "projectSlug": slug,
            "projectFile": project.get("project") or "",
            "schematicFile": project.get("schematic") or "",
            "boardFile": project.get("board") or "",
            "baseName": basename,
            "ercReport": erc.relative_to(project_site).as_posix(),
            "drcReport": drc.relative_to(project_site).as_posix(),
            "downloads": downloads,
            "pdfs": pdfs,
        }
        (project_site / "run-info.js").write_text(
            "window.HARDWARE_CI = {0};\n".format(json.dumps(info, indent=2)),
            encoding="utf-8",
        )
        for name in ("index.html", "style.css", "theme.js"):
            shutil.copy2(templates / name, project_site / name)

    write_index(out, templates, title, projects, statuses, run_url, sha)


def main():
    args = parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    if args.summary:
        page_url = os.environ.get("PAGE_URL", "")
        write_summary(out, page_url)
        return 0
    assemble(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
