param(
    [Parameter(Mandatory=$true)][string]$Branch,
    [Parameter(Mandatory=$true)][string]$FolderName,
    [string]$Base = "main"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".git")) {
    throw "Run BOOTSTRAP_NEW_REPO.ps1 first."
}

$parent = Split-Path $PSScriptRoot -Parent
$target = Join-Path $parent $FolderName
if (Test-Path $target) {
    throw "Target worktree already exists: $target"
}

# One active chat/writer per worktree. This helper does not reuse worktrees.
git worktree add -b $Branch $target $Base | Out-Host
Write-Host "WORKTREE_CREATED" -ForegroundColor Green
Write-Host "branch: $Branch"
Write-Host "path:   $target"
Write-Host "base:   $Base"
