param(
    [string]$TutorialRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Add-Error([string]$Message) { $errors.Add($Message) }
function Add-Warning([string]$Message) { $warnings.Add($Message) }

$expected = 35
$groups = @{
    'study_chapters' = 'chapter*.md'
    'source_archive' = 'chapter*.md'
    'full_chapters' = 'chapter*.md'
    'answer_keys' = 'chapter*.md'
}
foreach ($entry in $groups.GetEnumerator()) {
    $count = @(Get-ChildItem -LiteralPath (Join-Path $TutorialRoot $entry.Key) -File -Filter $entry.Value).Count
    if ($count -ne $expected) { Add-Error "$($entry.Key): expected $expected chapter files, got $count" }
}

$markdown = @(Get-ChildItem -LiteralPath $TutorialRoot -Recurse -File -Filter '*.md')
foreach ($file in $markdown) {
    $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $relative = $file.FullName.Substring($TutorialRoot.Length + 1)

    $fenceLines = @([regex]::Matches($raw, '(?m)^```.*$'))
    if (($fenceLines.Count % 2) -ne 0) { Add-Error "${relative}: unbalanced code fences" }

    $insideFence = $false
    foreach ($line in ($raw -split '\r?\n')) {
        if ($line -match '^```(.*)$') {
            $suffix = $Matches[1].Trim()
            if (-not $insideFence) {
                if ([string]::IsNullOrEmpty($suffix) -and $relative -like 'study_chapters*') {
                    Add-Error "${relative}: unlabeled opening code fence"
                }
                $insideFence = $true
            } else {
                $insideFence = $false
            }
        }
    }

    $h1Count = ([regex]::Matches($raw, '(?m)^#\s+')).Count
    if ($h1Count -ne 1) { Add-Error "${relative}: expected one H1, got $h1Count" }

    $previousLevel = 0
    foreach ($heading in [regex]::Matches($raw, '(?m)^(#{1,6})\s+')) {
        $level = $heading.Groups[1].Value.Length
        if ($previousLevel -gt 0 -and $level -gt ($previousLevel + 1)) {
            Add-Error "${relative}: heading jumps H$previousLevel to H$level"
        }
        $previousLevel = $level
    }

    foreach ($match in [regex]::Matches($raw, '(?<!!)\[[^\]]*\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim()
        if ($target -match '^(https?://|mailto:|#)') { continue }
        $pathOnly = ($target -split '#')[0]
        if ([string]::IsNullOrWhiteSpace($pathOnly)) { continue }
        $decoded = [uri]::UnescapeDataString($pathOnly)
        $resolved = Join-Path $file.DirectoryName $decoded
        if (-not (Test-Path -LiteralPath $resolved)) {
            Add-Error "${relative}: broken local link -> $target"
        }
    }

    foreach ($match in [regex]::Matches($raw, '!\[[^\]]*\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim()
        if ($target -match '^https?://') { continue }
        $resolved = Join-Path $file.DirectoryName (($target -split '#')[0])
        if (-not (Test-Path -LiteralPath $resolved)) {
            Add-Error "${relative}: missing image -> $target"
        }
    }
}

$studyFiles = @(Get-ChildItem -LiteralPath (Join-Path $TutorialRoot 'study_chapters') -File -Filter 'chapter*.md')
foreach ($file in $studyFiles) {
    $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    foreach ($required in @('本章学习结果','配套实验','自测答案','项目落点','原始资料','完整课程索引')) {
        if ($raw -notmatch [regex]::Escape($required)) { Add-Error "$($file.Name): missing study field '$required'" }
    }
    if ($raw -match '<table|<tr|<td') { Add-Error "$($file.Name): raw HTML table remains in study version" }
}

$archiveFiles = @(Get-ChildItem -LiteralPath (Join-Path $TutorialRoot 'source_archive') -File -Filter 'chapter*.md')
foreach ($file in $archiveFiles) {
    $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    if ($raw -notmatch '归档说明') { Add-Error "$($file.Name): missing archive warning" }
    if ($raw -notmatch 'https://zsc.github.io/isp_tutorial/') { Add-Error "$($file.Name): missing visible source URL" }
}

$labCount = @(Get-ChildItem -LiteralPath (Join-Path $TutorialRoot 'labs') -File -Filter 'lab*.md').Count
if ($labCount -lt 13) { Add-Error "labs: expected at least 13 lab documents, got $labCount" }
$assetCount = @(Get-ChildItem -LiteralPath (Join-Path $TutorialRoot 'assets') -File -Filter '*.png').Count
if ($assetCount -lt 8) { Add-Warning "assets: only $assetCount PNG files found" }

Write-Output "Markdown files checked: $($markdown.Count)"
Write-Output "Study/archive/landing/answer chapters: $($studyFiles.Count)/$($archiveFiles.Count)/$expected/$expected"
Write-Output "Labs: $labCount; PNG assets: $assetCount"

foreach ($warning in $warnings) { Write-Warning $warning }
if ($errors.Count -gt 0) {
    foreach ($courseError in $errors) { Write-Error $courseError }
    exit 1
}

Write-Output 'Course verification passed.'
