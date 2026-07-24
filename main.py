#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""FitFetch — FitGirl Repack Link Extractor.

Entry point.  All application logic lives under ``src/``.
"""

from __future__ import annotations

import sys

from src.app import run

if __name__ == "__main__":
    sys.exit(run())
