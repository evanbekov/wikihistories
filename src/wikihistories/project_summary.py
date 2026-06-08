from __future__ import annotations

import json
from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
README_TEMPLATE = ROOT / "README.template.md"
REPORT = ROOT / "report.json"


class MissingValue:
    def __init__(self, path: str):
        self.path = path

    def __getattr__(self, key: str) -> "MissingValue":
        return MissingValue(f"{self.path}.{key}")

    def __format__(self, format_spec: str) -> str:
        return "{" + self.path + "}"

    def __str__(self) -> str:
        return "{" + self.path + "}"


class ReportNamespace(dict[str, Any]):
    def __missing__(self, key: str) -> MissingValue:
        return MissingValue(key)

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
        except KeyError:
            return MissingValue(key)
        return value


def namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return ReportNamespace({key: namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [namespace(item) for item in value]
    return value


def load_report(path: Path = REPORT) -> ReportNamespace:
    if not path.exists():
        return ReportNamespace()
    return namespace(json.loads(path.read_text(encoding="utf-8")))


def write_report(report: dict[str, Any], path: Path = REPORT) -> Path:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def update_report_section(
    section: str,
    values: dict[str, Any],
    report_path: Path = REPORT,
) -> Path:
    report = load_report(report_path)
    report[section] = values
    return write_report(report, report_path)


def render_template(
    template_path: Path = README_TEMPLATE,
    report_path: Path = REPORT,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    report = load_report(report_path)
    return template.format_map(report)


def render_readme(
    readme_path: Path = README,
    template_path: Path = README_TEMPLATE,
    report_path: Path = REPORT,
) -> Path:
    readme_path.write_text(render_template(template_path, report_path), encoding="utf-8")
    return readme_path


def check_template_placeholders(
    template_path: Path = README_TEMPLATE,
    report_path: Path = REPORT,
) -> set[str]:
    template = template_path.read_text(encoding="utf-8")
    report = load_report(report_path)
    fields = {
        field_name.split(".", 1)[0]
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }
    return fields - set(report)
