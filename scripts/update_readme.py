#!/usr/bin/env python3
from __future__ import annotations

import argparse

from wikihistories.project_summary import (
    check_template_placeholders,
    render_readme,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render README.md from README.template.md and report.json."
    )
    parser.parse_args()

    missing = check_template_placeholders()
    if missing:
        raise SystemExit(
            "Missing values in report.json for placeholders: "
            + ", ".join(sorted(missing))
        )
    output = render_readme()
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
