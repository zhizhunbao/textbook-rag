"""Discover + capture all Canadian telecom carrier pages in ONE pass.

Single browser session per carrier: BFS discover links → expand → save PDF.
Skips pages that already have a valid PDF (>10KB).

Usage:
    uv run python scripts/crawl/discover_telecom.py --visible
    uv run python scripts/crawl/discover_telecom.py --visible --carriers publicmobile luckymobile
    uv run python scripts/crawl/discover_telecom.py --visible --max-pages 30
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Carrier config: (persona_slug, seed_url, url_filter_domains, supplemental_urls)
CARRIERS = {
    # Budget tier
    # "publicmobile" — SKIPPED: site Cloudflare-blocked, retry tomorrow (2026-05-19)
    # "publicmobile": {
    #     "persona": "telecom-publicmobile",
    #     "seed": "https://www.publicmobile.ca",
    #     "domains": {"www.publicmobile.ca", "publicmobile.ca"},
    #     "supplemental": [],
    # },
    "luckymobile": {
        "persona": "telecom-luckymobile",
        "seed": "https://www.luckymobile.ca",
        "domains": {"www.luckymobile.ca", "luckymobile.ca"},
        "supplemental": [
            "https://www.luckymobile.ca/shop/plans",
            "https://www.luckymobile.ca/shop/plans/prepaid",
            "https://www.luckymobile.ca/support",
            "https://www.luckymobile.ca/activate",
            "https://www.luckymobile.ca/tourist-esim",
        ],
    },
    "chatr": {
        "persona": "telecom-chatr",
        "seed": "https://www.chatrwireless.com",
        "domains": {"www.chatrwireless.com", "chatrwireless.com"},
        "supplemental": [
            "https://www.chatrwireless.com/plans",
            "https://www.chatrwireless.com/coverage",
            "https://www.chatrwireless.com/why-chatr",
            "https://www.chatrwireless.com/top-up",
            "https://www.chatrwireless.com/support",
            "https://www.chatrwireless.com/stores",
        ],
    },
    # Flanker tier
    "fido": {
        "persona": "telecom-fido",
        "seed": "https://www.fido.ca",
        "domains": {"www.fido.ca", "fido.ca"},
        "supplemental": [
            "https://www.fido.ca/phones/bring-your-own-device",
            "https://www.fido.ca/internet",
        ],
    },
    "koodo": {
        "persona": "telecom-koodo",
        "seed": "https://www.koodomobile.com",
        "domains": {"www.koodomobile.com", "koodomobile.com"},
        "supplemental": [
            "https://www.koodomobile.com/en/shop/mobility/bring-your-own-phone",
            "https://www.koodomobile.com/en/shop/subscriptions/internet",
        ],
    },
    "virginplus": {
        "persona": "telecom-virginplus",
        "seed": "https://www.virginplus.ca",
        "domains": {"www.virginplus.ca", "virginplus.ca"},
        "supplemental": [
            "https://www.virginplus.ca/en/plans",
            "https://www.virginplus.ca/en/why-virgin-plus",
        ],
    },
    "freedom": {
        "persona": "telecom-freedom",
        "seed": "https://www.freedommobile.ca",
        "domains": {"www.freedommobile.ca", "freedommobile.ca"},
        "supplemental": [
            "https://www.freedommobile.ca/en-CA/plans",
            "https://www.freedommobile.ca/en-CA/network-coverage",
            "https://www.freedommobile.ca/en-CA/special-offers",
            "https://www.freedommobile.ca/en-CA/home-internet",
        ],
    },
}

# ISP tier
ISP_CARRIERS = {
    "bell": {
        "persona": "internet-bell",
        "seed": "https://www.bell.ca/Bell_Internet",
        "domains": {"www.bell.ca", "bell.ca"},
        "supplemental": [],
    },
    "rogers": {
        "persona": "internet-rogers",
        "seed": "https://www.rogers.com/internet",
        "domains": {"www.rogers.com", "rogers.com"},
        "supplemental": [],
    },
    "teksavvy": {
        "persona": "internet-teksavvy",
        "seed": "https://www.teksavvy.com/internet",
        "domains": {"www.teksavvy.com", "teksavvy.com"},
        "supplemental": [],
    },
}


async def main():
    import argparse
    from urllib.parse import urlparse
    from engine_v2.crawling.web_crawler_v2 import discover_and_save_pdfs

    parser = argparse.ArgumentParser(description="Discover + capture telecom/ISP pages")
    parser.add_argument("--carriers", nargs="+",
                        default=list(CARRIERS.keys()),
                        help="Which carriers to crawl (default: all telecom)")
    parser.add_argument("--isp", action="store_true", help="Also include ISP carriers (Bell/Rogers/TekSavvy)")
    parser.add_argument("--isp-only", action="store_true", help="Only ISP carriers")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages per carrier")
    parser.add_argument("--max-depth", type=int, default=2, help="BFS depth")
    parser.add_argument("--delay", type=float, default=8.0, help="Delay between pages")
    args = parser.parse_args()

    # Build carrier list
    all_carriers = {}
    if not args.isp_only:
        for c in args.carriers:
            if c in CARRIERS:
                all_carriers[c] = CARRIERS[c]
    if args.isp or args.isp_only:
        all_carriers.update(ISP_CARRIERS)

    total_t0 = time.time()
    print("=" * 60)
    print(f"TELECOM DISCOVER+SAVE: {', '.join(c.upper() for c in all_carriers)}")
    print("=" * 60)

    for i, (name, cfg) in enumerate(all_carriers.items(), 1):
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(all_carriers)}] {name.upper()}")
        print(f"{'─'*60}")

        t0 = time.time()
        domains = cfg["domains"]

        def make_filter(doms):
            def url_filter(u):
                return urlparse(u).netloc in doms
            return url_filter

        try:
            results = await discover_and_save_pdfs(
                cfg["seed"],
                persona_slug=cfg["persona"],
                max_depth=args.max_depth,
                max_pages=args.max_pages,
                headless=not args.visible,
                delay_between=args.delay,
                url_filter=make_filter(domains),
                supplemental_urls=cfg["supplemental"] or None,
            )
            ok = sum(1 for r in results if r.success)
            print(f"  [{name.upper()}] {ok}/{len(results)} saved in {time.time()-t0:.0f}s")
        except Exception as e:
            print(f"  [{name.upper()}] ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"ALL DONE ({(time.time()-total_t0)/60:.1f} min)")
    print(f"{'='*60}")
    print("\nNext: ingest")
    for name, cfg in all_carriers.items():
        p = cfg["persona"]
        print(f"  uv run python scripts/ingest/batch_mineru.py --category {p}")


if __name__ == "__main__":
    asyncio.run(main())
