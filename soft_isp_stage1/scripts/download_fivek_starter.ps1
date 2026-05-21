$ErrorActionPreference = "Stop"

$base = "https://data.csail.mit.edu/graphics/fivek/img/dng"
$out = Join-Path $PSScriptRoot "..\data\raw"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$samples = @(
  @{ Name = "S01_a0001-jmac_DSC1459.dng"; Url = "$base/a0001-jmac_DSC1459.dng" },
  @{ Name = "S02_a0002-dgw_005.dng"; Url = "$base/a0002-dgw_005.dng" },
  @{ Name = "S03_a0003-NKIM_MG_8178.dng"; Url = "$base/a0003-NKIM_MG_8178.dng" },
  @{ Name = "S04_a0004-jmac_MG_1384.dng"; Url = "$base/a0004-jmac_MG_1384.dng" },
  @{ Name = "S05_a0005-jn_2007_05_10__564.dng"; Url = "$base/a0005-jn_2007_05_10__564.dng" }
)

foreach ($sample in $samples) {
  $target = Join-Path $out $sample.Name
  if (Test-Path $target) {
    Write-Host "Skip existing $($sample.Name)"
    continue
  }
  Write-Host "Downloading $($sample.Name)"
  Invoke-WebRequest -Uri $sample.Url -OutFile $target
}

