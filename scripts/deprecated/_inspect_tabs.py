"""Inspect Algonquin tab DOM structure."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(
        "https://www.algonquincollege.com/acce/program/automotive-service-technician-asep-gm/",
        wait_until="domcontentloaded",
    )
    page.wait_for_timeout(5000)

    # Find tab containers
    result = page.evaluate("""() => {
        const main = document.querySelector("main") || document.body;
        const containers = main.querySelectorAll("[class*='tab'], [class*='menu'], [class*='sidebar'], [class*='nav'], ul");
        const info = [];
        for (const c of containers) {
            const links = c.querySelectorAll("a");
            if (links.length >= 3) {
                info.push({
                    tag: c.tagName,
                    cls: c.className.substring(0, 100),
                    id: c.id,
                    linkCount: links.length,
                    links: Array.from(links).slice(0, 10).map(l => ({
                        text: l.textContent.trim().substring(0, 40),
                        href: l.getAttribute("href"),
                        cls: l.className.substring(0, 60),
                        tag: l.tagName,
                    }))
                });
            }
        }
        return info;
    }""")

    for item in result:
        print(f'\nContainer: <{item["tag"]} class="{item["cls"]}" id="{item["id"]}">')
        print(f'  Links: {item["linkCount"]}')
        for l in item["links"]:
            print(f'    "{l["text"]}" -> href={l["href"]} class={l["cls"]}')

    # Also check: what's the content panel structure?
    panels = page.evaluate("""() => {
        const main = document.querySelector("main") || document.body;
        const divs = main.querySelectorAll("div[id], section[id]");
        return Array.from(divs).slice(0, 20).map(d => ({
            tag: d.tagName,
            id: d.id,
            cls: d.className.substring(0, 80),
            visible: getComputedStyle(d).display !== 'none',
            childCount: d.children.length,
        }));
    }""")

    print("\n\n=== Content Panels ===")
    for p2 in panels:
        vis = "VISIBLE" if p2["visible"] else "HIDDEN"
        print(f'  <{p2["tag"]} id="{p2["id"]}" class="{p2["cls"]}"> [{vis}] children={p2["childCount"]}')

    browser.close()
