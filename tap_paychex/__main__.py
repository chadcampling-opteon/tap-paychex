"""Paychex entry point."""

from __future__ import annotations

from tap_paychex.tap import TapPaychex

TapPaychex.cli()
