# Re-clone all reference repos into .github/references
# Run in PowerShell from repo root: .\.github\references\clone-references.ps1

$ErrorActionPreference = "Stop"
$refDir = $PSScriptRoot

$repos = @(
  @{ Name = "DocLayout-YOLO"; Url = "https://github.com/opendatalab/DocLayout-YOLO.git" },
  @{ Name = "MinerU"; Url = "https://github.com/opendatalab/MinerU.git" },
  @{ Name = "PageIndex"; Url = "https://github.com/VectifyAI/PageIndex.git" },
  @{ Name = "ollama-python"; Url = "https://github.com/ollama/ollama-python.git" },
  @{ Name = "ollama-rag"; Url = "https://github.com/digithree/ollama-rag.git" },
  @{ Name = "sqlite-rag"; Url = "https://github.com/sqliteai/sqlite-rag.git" },
  @{ Name = "streamlit-pdf-viewer"; Url = "https://github.com/lfoppiano/streamlit-pdf-viewer.git" },
  @{ Name = "openclaw"; Url = "https://github.com/openclaw/openclaw.git" }
)

Set-Location $refDir

foreach ($r in $repos) {
  if (Test-Path $r.Name) {
    Write-Host "Remove existing: $($r.Name)"
    Remove-Item $r.Name -Recurse -Force
  }
  Write-Host "Cloning $($r.Name)..."
  git clone --depth 1 $r.Url $r.Name
}

Write-Host "Done. Directories:"
Get-ChildItem -Directory | ForEach-Object { $_.Name }
