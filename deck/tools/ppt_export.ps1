# Opens the PPTX in PowerPoint, exports each slide as PNG and the whole deck as PDF.
param([string]$Pptx, [string]$OutDir)
$ppt = New-Object -ComObject PowerPoint.Application
$pres = $ppt.Presentations.Open($Pptx, $true, $false, $false)
New-Item -ItemType Directory -Force $OutDir | Out-Null
$i = 1
foreach ($s in $pres.Slides) { $s.Export((Join-Path $OutDir "ppt_slide$i.png"), "PNG", 1920, 1080); $i++ }
$pdf = Join-Path $OutDir "from_powerpoint.pdf"
$pres.SaveAs($pdf, 32)
$pres.Close()
$ppt.Quit()
"exported $($i - 1) slides and $pdf"
