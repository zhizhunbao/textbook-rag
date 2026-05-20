"""Scan for prohibited/sensitive terms in publish config files."""
import sys, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PUBLISH_DIR = Path(__file__).resolve().parent.parent / ".agent" / "workflows" / "short-video" / "publish"

# 广告法违禁词 + 平台敏感词
TERMS = [
    "最好", "最佳", "第一", "首选", "100%", "绝对", "保证",
    "国家级", "世界级", "首创", "唯一", "顶级", "极致", "完美",
    "永久", "万能", "秒杀", "最强", "最优", "最大", "最快",
    # 平台敏感词
    "移民",
    # 金融违规
    "保本", "稳赚", "无风险", "高收益",
]

hits = []
for f in sorted(PUBLISH_DIR.rglob("*")):
    if f.suffix not in (".py", ".yaml", ".yml", ".md"):
        continue
    if "__pycache__" in str(f) or "node_modules" in str(f):
        continue
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    for i, line in enumerate(lines, 1):
        # Skip pure code/comment lines that won't be published
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("# "):
            continue
        for term in TERMS:
            if term in line:
                rel = f.relative_to(PUBLISH_DIR)
                hits.append((str(rel), i, term, stripped))

if hits:
    print(f"\n⚠️  发现 {len(hits)} 处潜在违规词:\n")
    for rel, lineno, term, text in hits:
        print(f"  [{term}] {rel}:L{lineno}")
        print(f"         {text[:80]}")
    print()
else:
    print("\n✅ 未发现违规词\n")
