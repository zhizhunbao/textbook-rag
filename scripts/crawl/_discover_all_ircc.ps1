# Discover all IRCC service categories into federal-ircc manifest
# Each discover merges into the existing manifest (no duplicates)

$seeds = @(
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/permanent-residents.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-passports.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/settle-canada.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/refugees.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/application.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/protect-fraud.html"
    # News & policy
    "https://www.canada.ca/en/immigration-refugees-citizenship/news.html"
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate.html"
)

Write-Host "=== Discovering $($seeds.Count) IRCC categories ===" -ForegroundColor Cyan

for ($i = 0; $i -lt $seeds.Count; $i++) {
    $url = $seeds[$i]
    $name = ($url -split '/')[-1] -replace '\.html$',''
    Write-Host "`n[$($i+1)/$($seeds.Count)] $name" -ForegroundColor Yellow
    uv run python scripts/crawl/crawler_cli.py discover $url federal-ircc --depth 3 --max-pages 200
}

Write-Host "`n=== Discovery complete! Now run: ===" -ForegroundColor Green
Write-Host "uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/federal-ircc/manifest.json"
