param(
    [string]$Repo = 'TetrisBattle-Educational',
    [ValidateSet('private','public')][string]$Visibility = 'private'
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
foreach ($command in @('git','gh')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command. Install Git and GitHub CLI first."
    }
}
& gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Run gh auth login first.' }
if ($Visibility -eq 'public') {
    Write-Warning 'Public publishing redistributes files currently in this directory. Review third-party media permissions before proceeding.'
    $choice = Read-Host 'Type YES to confirm you have permission to publish all included assets'
    if ($choice -cne 'YES') { throw 'Publication cancelled.' }
}
if (-not (Test-Path '.git')) {
    & git init
    if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
}
& git branch -M main
& git add -A
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    & git commit -m 'Prepare educational TetrisBattle edition with English docs and GIFs'
    if ($LASTEXITCODE -ne 0) { throw 'git commit failed; configure your Git user.name and user.email.' }
}
& git remote get-url origin *> $null
if ($LASTEXITCODE -eq 0) { throw 'An origin remote already exists. Review and push manually to prevent uploading to the wrong repository.' }
$visibilityFlag = if ($Visibility -eq 'private') { '--private' } else { '--public' }
& gh repo create $Repo $visibilityFlag --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'gh repo create failed. Check repository name and permissions.' }
Write-Host 'GitHub push completed.' -ForegroundColor Green
