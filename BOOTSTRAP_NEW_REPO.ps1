$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "===== CAP1 NEW REPO BOOTSTRAP =====" -ForegroundColor Cyan

if (Test-Path ".git") {
    Write-Host "Git repository already exists. No re-initialization performed." -ForegroundColor Yellow
    git status --short
    git branch --show-current
    git rev-parse --short HEAD
    exit 0
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not available in PATH. Install/repair Git first."
}

$gitName = (git config --global user.name 2>$null)
$gitEmail = (git config --global user.email 2>$null)
if (-not $gitName -or -not $gitEmail) {
    Write-Host "Git identity is missing. Configure it once, then rerun:" -ForegroundColor Yellow
    Write-Host '  git config --global user.name "Your Name"'
    Write-Host '  git config --global user.email "you@example.com"'
    throw "GIT_IDENTITY_MISSING"
}

try {
    git init -b main | Out-Host
} catch {
    git init | Out-Host
    git branch -M main
}

# Keep the first checkpoint deterministic and free from runtime artifacts.
git add .
$staged = git diff --cached --name-only
if (-not $staged) {
    throw "Nothing was staged for the initial checkpoint."
}

git commit -m "chore: bootstrap M0 code candidate" | Out-Host
$sha = (git rev-parse --short HEAD).Trim()

git branch checkpoint/m0-code-candidate
try {
    git tag -a m0-code-candidate-pre-gate -m "M0 code candidate before target-laptop local gate"
} catch {
    Write-Host "Tag already exists; continuing." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "BOOTSTRAP_REPO_PASS" -ForegroundColor Green
Write-Host "branch: main"
Write-Host "HEAD:   $sha"
Write-Host "checkpoint branch: checkpoint/m0-code-candidate"
Write-Host "tag: m0-code-candidate-pre-gate"
Write-Host ""
Write-Host "Next: give Codex Luna docs/CODEX_M0_LOCAL_GATE_PROMPT.md" -ForegroundColor Cyan
