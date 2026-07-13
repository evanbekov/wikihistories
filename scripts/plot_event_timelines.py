#!/usr/bin/env python3
from __future__ import annotations

from wikihistories.event_timelines import build_all


def main() -> None:
    for output in build_all():
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
