#!/usr/bin/env python3
"""Demo job: prints working directory and current time."""
import os
from datetime import datetime, timezone

cwd = os.getcwd()
now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

print("=" * 50)
print(f"  Working directory : {cwd}")
print(f"  Local time        : {now_local}")
print(f"  UTC time          : {now_utc}")
print("=" * 50)
