[CmdletBinding()]
param(
    [int]$Top = 20,
    [double]$WarnAboveMB = 50
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    # 关闭 Git 的非 ASCII 路径转义，避免中文文件名被引号和八进制序列包裹。
    $null = Get-Command git.exe -ErrorAction Stop
    $Tracked = @(git.exe -c core.quotepath=false ls-files)
    Write-Verbose "repo=$RepoRoot raw_tracked_count=$($Tracked.Count) first=$($Tracked | Select-Object -First 1)"
    $GitExitCode = $LASTEXITCODE
    if ($null -ne $GitExitCode -and $GitExitCode -ne 0) {
        throw "git ls-files failed"
    }

    $Rows = foreach ($Path in $Tracked) {
        if (Test-Path -LiteralPath $Path) {
            $Item = Get-Item -LiteralPath $Path
            [pscustomobject]@{
                Path = $Path
                SizeMB = [math]::Round($Item.Length / 1MB, 2)
            }
        }
    }

    $LfsCount = 0
    if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
        $LfsCount = @(git lfs ls-files).Count
    }

    $TotalBytes = ($Rows | Measure-Object SizeMB -Sum).Sum
    Write-Host "tracked_files=$($Tracked.Count)"
    Write-Host "lfs_files=$LfsCount"
    Write-Host "tracked_worktree_MB=$([math]::Round($TotalBytes, 2))"
    Write-Host "largest_tracked_files:"
    $Rows | Sort-Object SizeMB -Descending | Select-Object -First $Top | Format-Table -AutoSize

    $Oversized = @($Rows | Where-Object SizeMB -GT $WarnAboveMB | Sort-Object SizeMB -Descending)
    Write-Host "files_above_${WarnAboveMB}MB=$($Oversized.Count)"
    if ($Oversized.Count -gt 0) {
        $Oversized | Format-Table -AutoSize
    }
}
finally {
    Pop-Location
}
