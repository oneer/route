$ErrorActionPreference = "Stop"

$base = "https://data.csail.mit.edu/graphics/fivek/img/dng"
$out = Join-Path $PSScriptRoot "..\data\raw"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$samples = @(
  @{ Name = "T01_a0006-IMG_2787.dng"; Url = "$base/a0006-IMG_2787.dng" },
  @{ Name = "T02_a0008-WP_CRW_3959.dng"; Url = "$base/a0008-WP_CRW_3959.dng" },
  @{ Name = "T03_a0010-jmac_MG_4807.dng"; Url = "$base/a0010-jmac_MG_4807.dng" },
  @{ Name = "T04_a0012-kme_143.dng"; Url = "$base/a0012-kme_143.dng" },
  @{ Name = "T05_a0014-WP_CRW_6320.dng"; Url = "$base/a0014-WP_CRW_6320.dng" },
  @{ Name = "T06_a0018-kme_234.dng"; Url = "$base/a0018-kme_234.dng" },
  @{ Name = "T07_a0020-jmac_MG_6225.dng"; Url = "$base/a0020-jmac_MG_6225.dng" },
  @{ Name = "T08_a0022-IMG_2380.dng"; Url = "$base/a0022-IMG_2380.dng" },
  @{ Name = "T09_a0023-07-06-02-at-15h06m48-s_MG_1489.dng"; Url = "$base/a0023-07-06-02-at-15h06m48-s_MG_1489.dng" },
  @{ Name = "T10_a0026-kme_391.dng"; Url = "$base/a0026-kme_391.dng" },
  @{ Name = "T11_a0033-KE_-2590.dng"; Url = "$base/a0033-KE_-2590.dng" },
  @{ Name = "T12_a0034-LSYD4O2202.dng"; Url = "$base/a0034-LSYD4O2202.dng" },
  @{ Name = "T13_a0035-dgw_048.dng"; Url = "$base/a0035-dgw_048.dng" },
  @{ Name = "T14_a0040-_DSC5693.dng"; Url = "$base/a0040-_DSC5693.dng" }
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
