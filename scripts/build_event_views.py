#!/usr/bin/env python3
from __future__ import annotations

from wikihistories.event_views import build_all_event_views


def main() -> None:
    for output in build_all_event_views():
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
