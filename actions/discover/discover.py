#!/usr/bin/env python3
"""Find KiCad projects and apply the optional viewer config."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - the action installs PyYAML before running this
    yaml = None


BUILTIN_INCLUDE = "**/*.kicad_pro"
BUILTIN_EXCLUDE = ["**/output/**", "**/archive/**", "**/templates/**"]
BUILTIN_PRODUCTION = ["{dir}/production", "{dir}/fab", "{dir}/outputs"]
BUILTIN_KIBOT = "{dir}/{name}.kibot.yaml"
KIBOT_NAMES = ("checks", "outputs", "3d")


def compile_glob(pattern):
    parts = ["^"]
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    parts.append("$")
    return re.compile("".join(parts))


def matches_any(path, patterns):
    normalized = path.replace("\\", "/")
    return any(compile_glob(pattern).match(normalized) for pattern in patterns if pattern)


def split_patterns(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def git_projects(root):
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "*.kicad_pro"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*.kicad_pro"))
    text = result.stdout.decode("utf-8", errors="replace")
    return [item.replace("\\", "/") for item in text.split("\0") if item]


def schematic_title(path):
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'\(\s*title\s+"([^"]*)"', text)
    return match.group(1).strip() if match else ""


def folder_name(directory):
    name = Path(directory).name
    return name.replace("_", " ").replace("-", " ").strip().title() or "Board"


def slug_from_dir(directory):
    slug = re.sub(r"[/_\s]+", "-", directory.strip("/").lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "board"


def expand(value, directory, basename):
    text = str(value).replace("{dir}", directory).replace("{basename}", basename).replace("\\", "/")
    if not directory:
        text = text.lstrip("/")
    while text.startswith("./"):
        text = text[2:]
    return text


def load_config(path):
    if not path or not Path(path).is_file():
        return {}
    if yaml is None:
        raise SystemExit("PyYAML is required to read the viewer config. Install it with: pip install pyyaml")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Viewer config must be a mapping: {path}")
    return data


def first_existing(root, patterns, directory, basename):
    found = []
    for pattern in patterns:
        candidate = expand(pattern, directory, basename)
        if (root / candidate).is_dir():
            found.append(candidate)
    return found


def resolve_kibot(root, spec, directory, basename):
    resolved = {}
    if isinstance(spec, dict):
        aliases = {"model": "3d", "3d": "3d", "checks": "checks", "outputs": "outputs"}
        for key, name in aliases.items():
            if spec.get(key):
                resolved[name] = expand(spec[key], directory, basename)
    else:
        pattern = str(spec or BUILTIN_KIBOT)
        for name in KIBOT_NAMES:
            resolved[name] = expand(pattern, directory, basename).replace("{name}", name)
    return {name: path for name, path in resolved.items() if (root / path).is_file()}


def set_output(name, value):
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    delimiter = "KICAD_VIEWER_OUTPUT"
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def write_summary(projects):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    lines = [
        "## Discovered KiCad projects",
        "",
        "| Project | Slug | Path | Production | KiBot |",
        "| --- | --- | --- | --- | --- |",
    ]
    for project in projects:
        production = ", ".join(project["production"]) or "none"
        kibot = ", ".join(sorted(project["kibot"])) or "defaults"
        lines.append(
            f"| {project['name']} | `{project['slug']}` | `{project['dir']}` | {production} | {kibot} |"
        )
    if not projects:
        lines.append("| _none_ | | | | |")
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--include", default=BUILTIN_INCLUDE)
    parser.add_argument("--exclude", default=",".join(BUILTIN_EXCLUDE))
    parser.add_argument("--config", default=".github/kicad-viewer.yml")
    parser.add_argument("--production", default=",".join(BUILTIN_PRODUCTION))
    parser.add_argument("--kibot", default=BUILTIN_KIBOT)
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    config = load_config(root / args.config)
    defaults = config.get("defaults") or {}
    include = split_patterns(args.include) or [BUILTIN_INCLUDE]
    exclude = split_patterns(args.exclude)
    production_patterns = split_patterns(defaults.get("production", args.production))
    kibot_spec = defaults.get("kibot", args.kibot)
    production_is_list = isinstance(defaults.get("production"), list)

    discovered = []
    for project_file in git_projects(root):
        if not matches_any(project_file, include) or matches_any(project_file, exclude):
            continue
        directory = str(Path(project_file).parent).replace("\\", "/")
        if directory == ".":
            directory = ""
        basename = Path(project_file).stem
        schematic = f"{directory}/{basename}.kicad_sch" if directory else f"{basename}.kicad_sch"
        board = f"{directory}/{basename}.kicad_pcb" if directory else f"{basename}.kicad_pcb"
        schematic = schematic.lstrip("/")
        board = board.lstrip("/")
        if not (root / schematic).is_file():
            print(f"warning: {project_file} has no matching schematic {schematic}", file=sys.stderr)
            schematic = ""
        if not (root / board).is_file():
            print(f"warning: {project_file} has no matching board {board}", file=sys.stderr)
            board = ""
        title = schematic_title(root / schematic) if schematic else ""
        discovered.append({
            "project_file": project_file,
            "dir": directory,
            "basename": basename,
            "project": Path(project_file).name,
            "schematic_file": Path(schematic).name if schematic else "",
            "board_file": Path(board).name if board else "",
            "schematic": schematic,
            "board": board,
            "name": title or folder_name(directory or basename),
            "slug": slug_from_dir(directory or basename),
            "production_patterns": production_patterns,
            "production_keep_all": production_is_list,
            "kibot_spec": kibot_spec,
            "enabled": True,
        })

    entries = config.get("projects") or []
    if entries:
        by_path = {}
        for item in discovered:
            by_path.setdefault(item["dir"], []).append(item)
            by_path.setdefault(item["project_file"], []).append(item)
        selected = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("path"):
                raise SystemExit("Each projects entry needs a path")
            path = str(entry["path"]).replace("\\", "/").rstrip("/")
            matches = by_path.get(path, [])
            if not matches:
                print(f"warning: configured project was not found: {path}", file=sys.stderr)
                continue
            for item in matches:
                copied = dict(item)
                copied["enabled"] = entry.get("enabled", True)
                for key in ("name", "slug"):
                    if entry.get(key):
                        copied[key] = str(entry[key])
                if "production" in entry:
                    copied["production_patterns"] = split_patterns(entry["production"])
                    copied["production_keep_all"] = isinstance(entry["production"], list)
                if "kibot" in entry:
                    copied["kibot_spec"] = entry["kibot"]
                selected.append(copied)
        discovered = [item for item in selected if item["enabled"]]

    used = {}
    projects = []
    for item in discovered:
        slug = item["slug"]
        if slug in used:
            used[slug] += 1
            slug = f"{slug}-{used[slug]}"
        else:
            used[slug] = 1
        directory = item["dir"]
        basename = item["basename"]
        production = first_existing(root, item["production_patterns"], directory, basename)
        if production and not item["production_keep_all"]:
            production = production[:1]
        kibot = resolve_kibot(root, item["kibot_spec"], directory, basename)
        projects.append({
            "slug": slug,
            "name": item["name"],
            "dir": directory,
            "project": item["project"],
            "schematic": item["schematic_file"],
            "board": item["board_file"],
            "basename": basename,
            "checks_config": kibot.get("checks", ""),
            "outputs_config": kibot.get("outputs", ""),
            "model_config": kibot.get("3d", ""),
            "production": production,
            "kibot": kibot,
        })

    payload = json.dumps(projects, separators=(",", ":"))
    matrix = json.dumps({"include": projects}, separators=(",", ":"))
    set_output("projects", payload)
    set_output("matrix", matrix)
    write_summary(projects)
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
