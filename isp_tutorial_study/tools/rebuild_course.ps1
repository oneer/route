param(
    [string]$TutorialRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$fullDir = Join-Path $TutorialRoot 'full_chapters'
$studyDir = Join-Path $TutorialRoot 'study_chapters'
$archiveDir = Join-Path $TutorialRoot 'source_archive'
$answerDir = Join-Path $TutorialRoot 'answer_keys'
$assetDir = Join-Path $TutorialRoot 'assets'

foreach ($dir in @($studyDir, $archiveDir, $answerDir, $assetDir)) {
    [System.IO.Directory]::CreateDirectory($dir) | Out-Null
}

$outcomes = @{
    1='画出从光子到 RAW、RGB/YUV 的完整链路，并解释每个核心模块为什么存在。'
    2='解释 CMOS 像素、噪声、动态范围、增益和曝光之间的关系。'
    3='根据 CFA、sensor mode、metadata 和接口约束定义 ISP 输入契约。'
    4='在正确数据域完成 BLC、FPN、暗电流、线性化与 PRNU 校正。'
    5='区分并验证 shading、暗角、畸变和色差校正。'
    6='检测、分类并修复 Bayer RAW 中的单点与簇状缺陷。'
    7='比较双线性、边缘感知和 MHC 去马赛克的伪影与代价。'
    8='按噪声模型、处理域和时空维度选择降噪方法并评价失败案例。'
    9='解释 NLM 的质量—复杂度—访存取舍，并设计硬件友好近似。'
    10='区分 camera RGB、线性 RGB、sRGB、XYZ/Lab、YCbCr，并完成 AWB/CCM 评价。'
    11='用像素率、带宽、位宽、缓存和流控约束描述硬件 ISP。'
    12='计算 line buffer、tile overlap、SRAM bank 和 DDR 带宽。'
    13='解释时序、CDC、功耗、DVFS 和热约束如何改变 ISP 架构。'
    14='区分 HDR 采集、融合、去鬼影、tone mapping 和 HDR 显示。'
    15='从配准、运动、重建和系统代价评价计算摄影功能。'
    16='把 AE、AF、AWB 看作带延迟和稳定性约束的闭环控制系统。'
    17='基于公开证据分析移动 ISP 的异构计算、多摄、HDR 与功耗取舍。'
    18='区分 Apple 公开能力、合理推断和不可验证内部实现。'
    19='使用统一维度比较移动 ISP，而不是复述峰值参数和宣传词。'
    20='从功能安全、最坏延迟、同步、HDR/LFM 和降级理解车载 ISP。'
    21='依据任务、接口、生态、安全和证据质量完成车载平台初步选型。'
    22='为雨雾雪、夜间、LED、隧道和运动场景设计验证矩阵。'
    23='从 RAW 工作流、色彩、位深、连拍和视频评价专业相机 ISP。'
    24='计算高像素/高位深的数据压力，并解释 tile、预览与最终输出双流水线。'
    25='解释消费电子在成本、功耗、预览一致性、多摄切换和产品化调参上的取舍。'
    26='从低照、WDR、TNR、红外、隐私和编码评价安防 ISP。'
    27='以时域稳定、带宽、HDR/Log、色度采样和编码协同评价视频 ISP。'
    28='判断 AI 适合替代、增强还是预测哪些 ISP 环节，并设计 fallback。'
    29='从数据、损失、量化、带宽和 failure gallery 评价 AI ISP 模块。'
    30='比较 ISP 流水线、GPU SIMT、NPU 和异构调度的适用边界。'
    31='区分 ISP 增强与 Codec 压缩，并分析预处理对码率和时域质量的影响。'
    32='建立从单模块到系统、从画质到性能、从 directed 到 regression 的验证闭环。'
    33='解释综合、floorplan、STA、功耗、DFT、signoff 如何约束算法选择。'
    34='沿 buffer、metadata、DMA、HAL、功耗和恢复路径定位系统集成问题。'
    35='用证据成熟度、算力、数据、生态、安全和量产约束评价技术趋势。'
}

function Get-Phase([int]$Chapter) {
    if ($Chapter -le 10) { return '传统 ISP 与成像基础' }
    if ($Chapter -le 16) { return '硬件架构、HDR、计算摄影与 3A' }
    if ($Chapter -le 27) { return '产业平台与应用场景（选修）' }
    if ($Chapter -le 31) { return 'AI-ISP 与异构架构' }
    return '验证、实现、系统与趋势'
}

function Get-Level([int]$Chapter) {
    if ($Chapter -le 5) { return '入门' }
    if ($Chapter -le 16) { return '入门 → 中级' }
    if ($Chapter -le 27) { return '中级/选修' }
    return '中级 → 进阶'
}

function Get-Duration([int]$Chapter) {
    if ($Chapter -le 5) { return '2–3 小时阅读 + 1–2 小时实验' }
    if ($Chapter -le 16) { return '3–4 小时阅读 + 2–4 小时实验' }
    if ($Chapter -le 27) { return '2–3 小时阅读 + 1–2 小时证据分析' }
    return '3–4 小时阅读 + 2–4 小时实验'
}

function Get-Priority([int]$Chapter) {
    if ($Chapter -le 16 -or $Chapter -eq 28 -or $Chapter -eq 29 -or $Chapter -eq 32 -or $Chapter -eq 34) {
        return '核心'
    }
    return '选修/按方向'
}

function Get-Lab([int]$Chapter) {
    switch ($Chapter) {
        {$_ -le 3} { return 'lab01-raw与传感器身份契约.md' }
        {$_ -le 6} { return 'lab02-raw前端校正.md' }
        7 { return 'lab03-去马赛克与伪影.md' }
        {$_ -le 9} { return 'lab04-降噪与NLM.md' }
        10 { return 'lab05-色彩与3A.md' }
        {$_ -le 13} { return 'lab06-硬件数据流与定点.md' }
        {$_ -le 16} { return 'lab07-HDR计算摄影与3A稳定性.md' }
        {$_ -le 24} { return 'lab08-产业资料证据审计.md' }
        {$_ -le 27} { return 'lab09-视频场景与系统指标.md' }
        {$_ -le 29} { return 'lab10-AI-ISP训练与失败案例.md' }
        {$_ -le 31} { return 'lab11-异构性能与编码协同.md' }
        {$_ -le 34} { return 'lab12-验证部署与系统集成.md' }
        default { return 'lab13-技术趋势证据卡.md' }
    }
}

function Get-ProjectLinks([int]$Chapter) {
    switch ($Chapter) {
        {$_ -le 3} { return @(
            '[Stage 1 起点](../../stage1_soft_isp/materials/stage1_start_here.md)',
            '[RAW 检查脚本](../../stage1_soft_isp/scripts/01_inspect_raw.py)',
            '[RAW 数据契约](../../stage1_soft_isp/soft_isp/raw_contract.py)') }
        4 { return @('[BLC 实现](../../stage1_soft_isp/soft_isp/blc.py)','[BLC 实验脚本](../../stage1_soft_isp/scripts/06_apply_blc.py)') }
        5 { return @('[LSC 实现](../../stage1_soft_isp/soft_isp/lsc.py)','[LSC 实验脚本](../../stage1_soft_isp/scripts/14_apply_lsc.py)','[标定工具](../../stage1_soft_isp/soft_isp/calibration.py)') }
        6 { return @('[DPC 实现](../../stage1_soft_isp/soft_isp/dpc.py)','[坏点注入练习](../../stage1_soft_isp/exercises/week2_dpc_injection.py)') }
        7 { return @('[Demosaic 实现](../../stage1_soft_isp/soft_isp/demosaic.py)','[Demosaic 练习](../../stage1_soft_isp/exercises/week3_demosaic_todo.py)') }
        {$_ -le 9} { return @('[传统降噪实现](../../stage1_soft_isp/soft_isp/denoise.py)','[NLM 参考实现](../../stage1_soft_isp/openisp/nlm.py)','[C++ 降噪基准](../../stage3_cpp_isp/benchmarks/bench_denoise.cpp)') }
        10 { return @('[AWB 实现](../../stage1_soft_isp/soft_isp/awb.py)','[CCM 实现](../../stage1_soft_isp/soft_isp/ccm.py)','[ColorChecker 标定](../../stage1_soft_isp/scripts/21_calibrate_colorchecker.py)') }
        {$_ -le 13} { return @('[Stage 3 C++ ISP](../../stage3_cpp_isp/README.md)','[Pipeline benchmark](../../stage3_cpp_isp/benchmarks/bench_pipeline.cpp)','[测试向量清单](../../stage3_cpp_isp/data/test_vectors_manifest.csv)') }
        14 { return @('[Tone 实现](../../stage1_soft_isp/soft_isp/tone.py)','[C++ tone benchmark](../../stage3_cpp_isp/benchmarks/bench_tone_mapping.cpp)','[HDR/LTM 数据](../../stage3_cpp_isp/data/week7_alignment)') }
        15 { return @('[图像融合 benchmark](../../stage3_cpp_isp/benchmarks/bench_image_fusion.cpp)','[多摄融合报告](../../stage3_cpp_isp/reports/multicamera_calibration_and_fusion.md)') }
        16 { return @('[统计模块](../../stage1_soft_isp/soft_isp/stats.py)','[高级 AWB](../../stage1_soft_isp/soft_isp/awb_advanced.py)','[相机系统采集协议](../../camera_system_capstone/reports/capture_protocol.md)') }
        {$_ -le 24} { return @('[相机系统综合项目](../../camera_system_capstone/README.md)','[多摄评价](../../camera_system_capstone/scripts/03_run_multicamera_evaluation.py)','[系统岗位证据矩阵](../../camera_system_capstone/outputs/job_evidence_matrix.csv)') }
        {$_ -le 27} { return @('[系统性能分析](../../camera_system_capstone/scripts/04_run_system_profile.py)','[Stage 3 pipeline benchmark](../../stage3_cpp_isp/benchmarks/bench_pipeline.cpp)','[Stage 4 设备流水线分析](../../stage4_deploy_isp/scripts/13_profile_device_pipeline.py)') }
        {$_ -le 29} { return @('[Stage 2 起点](../../stage2_ai_isp/stage2_start_here.md)','[AI-ISP 训练脚本](../../stage2_ai_isp/scripts/01_train_toy_rgb.py)','[场景失败矩阵](../../stage2_ai_isp/scripts/25_export_scene_failure_matrix.py)') }
        30 { return @('[C++ benchmarks](../../stage3_cpp_isp/benchmarks)','[设备流水线](../../stage4_deploy_isp/cpp/src/device_pipeline.cpp)','[质量-延迟-内存矩阵](../../stage4_deploy_isp/outputs/device_pipeline/quality_latency_memory_matrix.csv)') }
        31 { return @('[视频/系统性能分析](../../camera_system_capstone/scripts/04_run_system_profile.py)','[FFmpeg 可配套外部实验](../labs/lab11-异构性能与编码协同.md)') }
        32 { return @('[Stage 1 IQ 指标](../../stage1_soft_isp/soft_isp/iq_metrics.py)','[Stage 2 测试](../../stage2_ai_isp/tests)','[综合项目测试](../../camera_system_capstone/tests)') }
        33 { return @('[Stage 3 CMake 工程](../../stage3_cpp_isp/CMakeLists.txt)','[Stage 4 CMake/部署工程](../../stage4_deploy_isp/CMakeLists.txt)') }
        34 { return @('[相机系统综合项目](../../camera_system_capstone/README.md)','[系统优化报告](../../camera_system_capstone/reports/system_optimization_report.md)','[设备 pipeline contract](../../stage4_deploy_isp/configs/deployment_contract.yaml)') }
        default { return @('[四阶段学习路线](../../study-roadmap/阶段1-4 ISP项目升级方案报告.md)','[相机系统综合项目](../../camera_system_capstone/README.md)') }
    }
}

function Normalize-Guide([string]$Text) {
    $normalized = [regex]::Replace(
        $Text,
        '(?m)^(#{3,6})(\s+)',
        { param($match) ('#' * ($match.Groups[1].Value.Length - 1)) + $match.Groups[2].Value }
    )
    $normalized = [regex]::Replace($normalized, '(?:\r?\n){3,}', "`r`n`r`n")
    $insideFence = $false
    $labeled = [System.Collections.Generic.List[string]]::new()
    foreach ($line in ($normalized -split '\r?\n')) {
        if ($line -match '^```(.*)$') {
            $suffix = $Matches[1].Trim()
            if (-not $insideFence) {
                $labeled.Add($(if ([string]::IsNullOrEmpty($suffix)) { '```text' } else { $line }))
                $insideFence = $true
            } else {
                $labeled.Add('```')
                $insideFence = $false
            }
        } else {
            $labeled.Add($line)
        }
    }
    return (($labeled -join "`r`n").Trim())
}

function Set-Utf8([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText($Path, ($Content.TrimEnd() + "`r`n"), $utf8)
}

$files = @(Get-ChildItem -LiteralPath $fullDir -File -Filter 'chapter*.md' | Sort-Object Name)
$manifest = [System.Collections.Generic.List[object]]::new()

for ($fileIndex = 0; $fileIndex -lt $files.Count; $fileIndex++) {
    $file = $files[$fileIndex]
    $chapter = [int]([regex]::Match($file.Name, 'chapter(\d+)').Groups[1].Value)
    $title = ([regex]::Match($file.Name, 'chapter\d+-(.+)\.md$').Groups[1].Value)
    $studyPath = Join-Path $studyDir $file.Name
    $archivePath = Join-Path $archiveDir $file.Name
    $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8

    if ($raw -match '<!--\s*来源：' -and -not (Test-Path -LiteralPath $archivePath)) {
        $sourceUrl = [regex]::Match($raw, '<!--\s*来源：([^\s]+)\s*-->').Groups[1].Value
        $firstH2 = [regex]::Match($raw, '(?m)^##\s+')
        if (-not $firstH2.Success) { throw "No source-body H2 found in $($file.Name)" }

        $beforeH2 = $raw.Substring(0, $firstH2.Index)
        $separators = [regex]::Matches($beforeH2, '(?:\r?\n){4,}')
        if ($separators.Count -gt 0) {
            $separator = $separators[$separators.Count - 1]
            $guideRaw = $beforeH2.Substring(0, $separator.Index)
            $sourceIntro = $beforeH2.Substring($separator.Index + $separator.Length).Trim()
        } else {
            $guideRaw = $beforeH2
            $sourceIntro = ''
        }

        $guideRaw = [regex]::Replace($guideRaw, '(?m)^<!--.*?-->\s*', '')
        $guide = Normalize-Guide $guideRaw
        $sourceBody = (($sourceIntro + "`r`n`r`n" + $raw.Substring($firstH2.Index)).Trim())

        if ($chapter -eq 10) {
            $sourceBody = $sourceBody.Replace(
                'RGB是ISP处理的基础色彩空间，直接对应图像传感器的拜耳模式输出。在线性RGB空间中，色彩值与光强度成正比关系：',
                'RGB是 ISP 中重要的颜色表示，但 Bayer RAW 只是按 CFA 交错采样的单通道马赛克，并不是完整 RGB；完成去马赛克后才得到每像素三通道的 camera RGB。在线性 RGB 空间中，数值与光强近似成正比：')
        }
        if ($chapter -eq 16) {
            $sourceBody = $sourceBody.Replace('- 50Hz地区：8.33ms、16.67ms、25ms…', '- 50Hz 地区：10ms、20ms、30ms…（理想阻性光源常见 100Hz 光强周期；实际 LED/PWM 需实测）')
            $sourceBody = $sourceBody.Replace('- 60Hz地区：8.33ms、16.67ms…', '- 60Hz 地区：8.33ms、16.67ms、25ms…（理想阻性光源常见 120Hz 光强周期；实际 LED/PWM 需实测）')
        }

        $archiveWarning = @"
> **归档说明**：这是原网页正文的资料归档，不是本课程主学习路径。原文中的厂商内部架构、性能数字和“最新”表述不保证仍然有效；学习时以公开一手资料和 [来源分级规范](../SOURCE_POLICY.md) 为准。
>
> 原网页：<$sourceUrl>　归档整理：2026-07-19
"@
        if ($chapter -eq 18) {
            $archiveWarning += "`r`n> **特别勘误**：原文关于 A17 Pro 的 15 级 ISP 流水线、缓存容量、256-bit 专用总线、单核 MAC 数和 35 TOPS 等细节未得到 Apple 公开资料证实，均应视为 **[待核实]**，不得作为确定架构事实引用。`r`n"
        }

        $archive = "# 原教程正文归档：$title`r`n`r`n$archiveWarning`r`n`r`n$sourceBody"
        Set-Utf8 $archivePath $archive

        $priority = Get-Priority $chapter
        $phase = Get-Phase $chapter
        $level = Get-Level $chapter
        $duration = Get-Duration $chapter
        $lab = Get-Lab $chapter
        $projectLinks = (Get-ProjectLinks $chapter) -join "`r`n  - "
        $evidenceNote = if (($chapter -ge 17 -and $chapter -le 24) -or $chapter -eq 35) {
            '> **证据提醒**：本章涉及厂商、产品或趋势。正文中的参数必须结合资料日期阅读；公开事实、厂商宣传、第三方分析和合理推断不能混为一类。'
        } else {
            '> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。'
        }

        $metadata = @"
> 课程阶段：$phase　|　难度：$level　|　优先级：$priority
>
> 建议用时：$duration　|　内容整理：2026-07-19

$evidenceNote

本章学习结果：**$($outcomes[$chapter])**
"@

        $guide = [regex]::Replace($guide, '(?m)^(# .+)$', "`$1`r`n`r`n$metadata", 1)
        if ($chapter -eq 3 -or $chapter -eq 5) {
            $guide += @"

## 补充自测题

1. 用一句话说明本章对象的输入、处理和输出。
2. 哪一个参数或前置假设最容易设置错误？错误图像现象是什么？
3. 设计一个最小实验，说明如何区分算法问题、输入契约问题和标定问题。
"@
        }
        if ($chapter -le 5) {
            $guide += @"

## 学习优先级

- **必须掌握**：本章学习结果、输入输出、关键失败现象和最小验证方法。
- **了解即可**：历史背景、少见硬件变种和暂时无法从公开资料验证的细节。
- **后面再回看**：需要真实 RAW、标定数据或硬件经验才能完整理解的内容。
"@
        }

        $previousLink = if ($fileIndex -gt 0) { "[上一章](./$($files[$fileIndex - 1].Name))" } else { '[课程首页](../README.md)' }
        $nextLink = if ($fileIndex -lt ($files.Count - 1)) { "[下一章](./$($files[$fileIndex + 1].Name))" } else { '[课程首页](../README.md)' }
        $guide += @"

$(if ($chapter -ge 17) { @"
## 可追溯资料入口

- [按章节映射的参考资料](../research_bibliography.md#按章节映射的一手入口)
- [来源、证据等级与时效规范](../SOURCE_POLICY.md)
- 本章涉及的产品参数必须记录型号、版本、发布日期/访问日期和证据等级。

"@ } else { @"
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

"@ })
## 本章学习闭环

- 配套实验：[$lab](../labs/$lab)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/$($file.Name))
- 项目落点：
  - $projectLinks
- 原始资料：[原教程正文归档](../source_archive/$($file.Name))

导航：$previousLink · $nextLink · [完整课程索引](../full_content_index.md)
"@
        Set-Utf8 $studyPath $guide
    }

    if (-not (Test-Path -LiteralPath $studyPath) -or -not (Test-Path -LiteralPath $archivePath)) {
        throw "Missing split output for $($file.Name)"
    }

    $labName = Get-Lab $chapter
    $priority = Get-Priority $chapter
    $landing = @"
# $title

> 原长文已拆分为学习版和原文归档。请优先阅读学习版；本页保留原路径兼容性。

- [学习版正文](../study_chapters/$($file.Name))
- [配套实验](../labs/$labName)
- [自测答案与评分要点](../answer_keys/$($file.Name))
- [原教程正文归档](../source_archive/$($file.Name))
- [ISP 视觉图谱](../VISUAL_ATLAS.md)
- [完整课程索引](../full_content_index.md)

学习结果：**$($outcomes[$chapter])**

课程属性：$(Get-Phase $chapter) · $(Get-Level $chapter) · $priority
"@
    Set-Utf8 $file.FullName $landing

    $answer = @"
# 第 $chapter 章自测答案与评分要点

本答案采用“关键点 rubric”，用于检查理解，不鼓励逐字背诵。原正文中的开放题只要证据充分、假设明确，可以有不同答案。

本章专属概念见 [35 章自测专属关键点](README.md)，通用判分见 [统一评分标准](../SELF_TEST_RUBRIC.md)。

## 核心答案

1. **一句话目标**：$($outcomes[$chapter])
2. **输入输出**：答案必须明确数据形态或系统边界，不能只写算法名称；至少说明线性/非线性、RAW/RGB/YUV、位深或接口中的两项。
3. **顺序与依赖**：必须指出至少一个前置假设，以及顺序错误如何向后传播。
4. **参数与失败现象**：至少给出一组“参数过小/过大 → 可观察现象 → 定位手段”。
5. **最小验证**：必须包含固定输入、对照组、输出、至少一个数值指标和至少一个局部视觉检查。

## 10 分评分

| 项目 | 分值 | 通过条件 |
|---|---:|---|
| 概念与直觉 | 2 | 能用自己的话说明为什么需要本章内容 |
| 输入、处理、输出 | 2 | 数据域和接口明确 |
| 公式/参数 | 2 | 变量、单位或数量级合理 |
| 失败分析 | 2 | 能把图像或系统现象对应到原因 |
| 实验设计 | 2 | 输入、步骤、输出和判据完整 |

8–10 分：通过；6–7 分：回看实验与失败案例；低于 6 分：重新学习本章核心段落后再测。

[返回学习版](../study_chapters/$($file.Name)) · [配套实验](../labs/$(Get-Lab $chapter))
"@
    Set-Utf8 (Join-Path $answerDir $file.Name) $answer

    $manifest.Add([pscustomobject]@{
        Chapter=$chapter
        Title=$title
        Phase=Get-Phase $chapter
        Level=Get-Level $chapter
        Priority=$priority
        Lab=$labName
        StudyFile="study_chapters/$($file.Name)"
        ArchiveFile="source_archive/$($file.Name)"
    })
}

$manifest | Export-Csv -LiteralPath (Join-Path $TutorialRoot 'course_manifest.csv') -NoTypeInformation -Encoding UTF8

$assetCopies = @{
    'traditional_pipeline_compare.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_week4_pipeline_compare.png'
    'blc_visual_compare.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_blc_visual_compare.png'
    'lsc_compare.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_lsc_compare.png'
    'dpc_repair_crop.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_dpc_repair_crop.png'
    'demosaic_compare.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_week6_demosaic_compare.png'
    'awb_compare.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_week6_awb_compare.png'
    'ccm_deltae.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_week6_ccm_deltae.png'
    'tone_curves.png'='stage1_soft_isp\reports\figures\T01_a0006-IMG_2787_week6_tone_curves.png'
    'ai_failure_gallery.png'='stage2_ai_isp\reports\figures\week8_failure_case_crops\failure_case_crop_sheet.png'
    'ai_metrics_plot.png'='stage2_ai_isp\reports\figures\week4_sidd_tiny_standard_eval\metrics_plot.png'
    'onnx_error_map.png'='stage4_deploy_isp\outputs\week1_onnx\pytorch_vs_ort_error_maps\pair_00001_ort_vs_pytorch_error_x1000.png'
}
$repoRoot = Split-Path -Parent $TutorialRoot
foreach ($entry in $assetCopies.GetEnumerator()) {
    $source = Join-Path $repoRoot $entry.Value
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $assetDir $entry.Key) -Force
    }
}

Write-Output "Rebuilt $($manifest.Count) course chapters."
