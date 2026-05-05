"""Analyze topic coverage of crawled 456 pages."""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

m = json.load(open("data/crawled_web/edu-school-planning/manifest.json", "r", encoding="utf-8"))
pages = m["pages"]

# Categorize URLs by topic
cats = {}
for p in pages:
    url = p["url"]
    parts = url.split("/services/")
    if len(parts) > 1:
        topic = parts[1].split("/")[0]
    elif "/corporate/" in url:
        topic = "corporate/admin"
    elif "/campaigns/" in url:
        topic = "campaigns"
    elif "/news/" in url:
        topic = "news/notices"
    else:
        topic = "other"
    cats[topic] = cats.get(topic, 0) + 1

print("=" * 60)
print("456 Pages - Topic Distribution")
print("=" * 60)
for t, c in sorted(cats.items(), key=lambda x: -x[1]):
    pct = c / 456 * 100
    bar = "#" * int(pct / 2)
    print(f"  {t:<50s} {c:4d}  ({pct:5.1f}%) {bar}")
print("-" * 60)
print(f"  {'TOTAL':<50s} {sum(cats.values()):4d}")

# Check for key scenarios
print("\n" + "=" * 60)
print("Key Scenario Coverage Check")
print("=" * 60)

scenarios = {
    "Study Permit": ["study-permit", "extend-study-permit"],
    "PGWP": ["after-graduation", "work-after-graduation"],
    "Work Permit": ["work-canada", "work-permit", "hire-temporary"],
    "Express Entry": ["express-entry"],
    "Provincial Nominee": ["provincial-nominees"],
    "Family Sponsorship": ["family-sponsorship", "spouse-partner"],
    "Visitor Visa": ["visit-canada", "visitor-visa", "eta"],
    "Citizenship": ["canadian-citizenship", "become-canadian"],
    "DLI List": ["designated-learning-institution"],
    "Biometrics": ["biometrics"],
    "Medical Exam": ["medical-exam", "medical-police"],
    "Application Forms": ["application-forms-guides", "imm5"],
    "Processing Times": ["processing-times", "check-status"],
    "Super Visa": ["super-visa", "parent-grandparent"],
    "Atlantic Immigration": ["atlantic-immigration"],
    "Rural/Franco Pilots": ["rural-franco"],
    "Hong Kong PR": ["hong-kong"],
    "Caregiver Programs": ["caregiver"],
    "Passport": ["passport"],
    "Refugee": ["refugee"],
}

for scenario, keywords in scenarios.items():
    matched = []
    for p in pages:
        url = p["url"].lower()
        if any(kw in url for kw in keywords):
            matched.append(p["url"])
    status = "[OK]" if matched else "[MISS]"
    print(f"  {status:8s} {scenario:<40s} -> {len(matched)} pages")

# Identify potential noise/low-value pages
print("\n" + "=" * 60)
print("Potential Low-Value Pages (noise)")
print("=" * 60)
noise_keywords = ["careers", "transparency", "social-media", "terms-conditions", "accessibility"]
noise_count = 0
for p in pages:
    url = p["url"].lower()
    if any(kw in url for kw in noise_keywords):
        noise_count += 1
        print(f"  [noise] {p['url']}")
print(f"\n  Total noise pages: {noise_count}")
print(f"  Effective coverage: {456 - noise_count} pages")
