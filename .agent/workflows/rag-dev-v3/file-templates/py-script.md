# 1.9 `scripts/<verb>_<noun>.py` — 独立脚本

```python
"""<verb>_<noun> — <一句话描述>.

Usage:
    python -m scripts.<verb>_<noun> [--flag]
"""


from __future__ import annotations

import argparse
import sys

from loguru import logger


# ============================================================
# Main
# ============================================================
def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="<描述>")
    # parser.add_argument("--flag", ...)
    args = parser.parse_args()

    logger.info("Starting <verb>_<noun> ...")
    # TODO: implement
    logger.info("Done.")


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    main()
```
