#!/usr/bin/env python3
"""Compatibility entry point for the production Colour Lab browser gate.

The Stage-era harness was retired by the greenfield Workbench cutover. Keep the
old command name working so operator notes and local scripts cannot accidentally
run stale selectors against the production DOM.
"""
from __future__ import annotations

from verify_workbench import main


if __name__ == "__main__":
    raise SystemExit(main())
