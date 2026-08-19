Add-Type -AssemblyName System.Drawing

$outDir = "C:\Users\Brunna\Download\claude\caderneta-rendimentos\playstore-assets"

# Palette
$paper   = [System.Drawing.ColorTranslator]::FromHtml("#F3EFE4")
$paper2  = [System.Drawing.ColorTranslator]::FromHtml("#EAE3D2")
$ink     = [System.Drawing.ColorTranslator]::FromHtml("#241A10")
$inkMute = [System.Drawing.ColorTranslator]::FromHtml("#7A6F5C")
$verde   = [System.Drawing.ColorTranslator]::FromHtml("#1B6B4A")
$verdeLt = [System.Drawing.ColorTranslator]::FromHtml("#E4EFE7")
$ouro    = [System.Drawing.ColorTranslator]::FromHtml("#9C6B12")
$border  = [System.Drawing.ColorTranslator]::FromHtml("#D9D0BC")
$white   = [System.Drawing.Color]::White

function New-Canvas($w, $h, $bg) {
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear($bg)
    return @{ bmp = $bmp; g = $g }
}

function Draw-RoundRect($g, $pen, $brush, $x, $y, $w, $h, $r) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($x, $y, $r, $r, 180, 90)
    $path.AddArc($x + $w - $r, $y, $r, $r, 270, 90)
    $path.AddArc($x + $w - $r, $y + $h - $r, $r, $r, 0, 90)
    $path.AddArc($x, $y + $h - $r, $r, $r, 90, 90)
    $path.CloseFigure()
    if ($brush) { $g.FillPath($brush, $path) }
    if ($pen) { $g.DrawPath($pen, $path) }
    $path.Dispose()
}

function Draw-Text($g, $text, $font, $brush, $x, $y) {
    $g.DrawString($text, $font, $brush, $x, $y)
}

function Draw-Brand($g, $x, $y) {
    $iconBrush = New-Object System.Drawing.SolidBrush($verde)
    Draw-RoundRect $g $null $iconBrush $x $y 56 56 14
    $fIcon = New-Object System.Drawing.Font("Georgia", 22, [System.Drawing.FontStyle]::Bold)
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $rect = New-Object System.Drawing.RectangleF($x, $y, 56, 56)
    $g.DrawString("R$", $fIcon, (New-Object System.Drawing.SolidBrush($paper)), $rect, $sf)
    $fBrand = New-Object System.Drawing.Font("Georgia", 21, [System.Drawing.FontStyle]::Bold)
    $g.DrawString("Caderneta de Investimentos", $fBrand, (New-Object System.Drawing.SolidBrush($ink)), ($x + 72), ($y + 14))
}

# ---------- SCREENSHOT 1 : Hero ----------
$c = New-Canvas 1080 1920 $paper
$g = $c.g
Draw-Brand $g 64 70

$fTitle = New-Object System.Drawing.Font("Georgia", 58, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Quanto o seu`ndinheiro rende`nde verdade?", $fTitle, (New-Object System.Drawing.SolidBrush($ink)), 64, 190)

$fSub = New-Object System.Drawing.Font("Segoe UI", 26)
$g.DrawString("Caixinhas, cofrinhos e investimentos, tudo num`nso lugar - com a taxa CDI sempre atualizada.", $fSub, (New-Object System.Drawing.SolidBrush($inkMute)), 64, 480)

# CDI badge
$badgeBrush = New-Object System.Drawing.SolidBrush($white)
$badgePen = New-Object System.Drawing.Pen($border, 2)
Draw-RoundRect $g $badgePen $badgeBrush 64 620 500 130 20
$fLabel = New-Object System.Drawing.Font("Segoe UI", 18)
$g.DrawString("CDI ATUAL", $fLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 96, 650)
$fBig = New-Object System.Drawing.Font("Consolas", 44, [System.Drawing.FontStyle]::Bold)
$g.DrawString("13,90% ao ano", $fBig, (New-Object System.Drawing.SolidBrush($verde)), 96, 680)

# fake chart card
Draw-RoundRect $g $badgePen $badgeBrush 64 800 952 260 20
$fLabel2 = New-Object System.Drawing.Font("Segoe UI", 18)
$g.DrawString("EVOLUCAO DO CDI (ULTIMOS 6 MESES)", $fLabel2, (New-Object System.Drawing.SolidBrush($inkMute)), 96, 830)
$chartPen = New-Object System.Drawing.Pen($verde, 5)
$pts = @(
    (New-Object System.Drawing.Point(110, 990)),
    (New-Object System.Drawing.Point(280, 970)),
    (New-Object System.Drawing.Point(450, 975)),
    (New-Object System.Drawing.Point(620, 940)),
    (New-Object System.Drawing.Point(790, 935)),
    (New-Object System.Drawing.Point(960, 900))
)
$g.DrawLines($chartPen, $pts)
foreach ($p in $pts) { $g.FillEllipse((New-Object System.Drawing.SolidBrush($verde)), $p.X - 7, $p.Y - 7, 14, 14) }

# feature bullets
$fBul = New-Object System.Drawing.Font("Segoe UI", 24)
$bullets = @("Compare mais de uma dezena de bancos e corretoras", "Veja o rendimento liquido, ja descontando o IR", "Combine investimentos e descubra a melhor divisao")
$by = 1140
foreach ($b in $bullets) {
    $g.FillEllipse((New-Object System.Drawing.SolidBrush($verde)), 64, $by + 12, 16, 16)
    $g.DrawString($b, $fBul, (New-Object System.Drawing.SolidBrush($ink)), 100, $by)
    $by += 70
}

$c.bmp.Save("$outDir\screenshot-1-hero.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $c.bmp.Dispose()

# ---------- SCREENSHOT 2 : Total + projecao ----------
$c = New-Canvas 1080 1920 $paper
$g = $c.g
Draw-Brand $g 64 70

$fH2 = New-Object System.Drawing.Font("Georgia", 42, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Veja o total certinho`nda sua caderneta", $fH2, (New-Object System.Drawing.SolidBrush($ink)), 64, 190)

# total card
$cardBrush = New-Object System.Drawing.SolidBrush($white)
$cardPen = New-Object System.Drawing.Pen($border, 2)
Draw-RoundRect $g $cardPen $cardBrush 64 380 952 300 24
$g.DrawString("TOTAL NESTA CADERNETA", (New-Object System.Drawing.Font("Segoe UI", 20)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 420)
$g.DrawString("APLICADO HOJE", (New-Object System.Drawing.Font("Segoe UI", 18)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 470)
$g.DrawString("R`$ 59.500,00", (New-Object System.Drawing.Font("Consolas", 52, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($ink)), 96, 500)
$g.DrawString("RENDIMENTO NO MES 1", (New-Object System.Drawing.Font("Segoe UI", 18)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 590)
$g.DrawString("+ R`$ 602,22", (New-Object System.Drawing.Font("Consolas", 38, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($verde)), 96, 620)

# projection table card
Draw-RoundRect $g $cardPen $cardBrush 64 730 952 560 24
$g.DrawString("PROJECAO DA SUA CADERNETA", (New-Object System.Drawing.Font("Segoe UI", 20)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 770)

$rows = @(
    @{ m = "Mes 1"; saldo = "R`$ 60.102,22"; rend = "+ R`$ 602,22" },
    @{ m = "Mes 2"; saldo = "R`$ 60.710,57"; rend = "+ R`$ 608,35" },
    @{ m = "Mes 3"; saldo = "R`$ 61.325,11"; rend = "+ R`$ 614,53" }
)
$fRowLabel = New-Object System.Drawing.Font("Segoe UI", 22)
$fRowVal = New-Object System.Drawing.Font("Consolas", 24, [System.Drawing.FontStyle]::Bold)
$ry = 850
$g.DrawString("MES", $fRowLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 100, $ry)
$g.DrawString("SALDO TOTAL", $fRowLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 320, $ry)
$g.DrawString("RENDIMENTO", $fRowLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 700, $ry)
$ry += 60
$g.DrawLine((New-Object System.Drawing.Pen($border, 2)), 100, $ry, 950, $ry)
$ry += 30
foreach ($row in $rows) {
    $g.DrawString($row.m, $fRowVal, (New-Object System.Drawing.SolidBrush($ink)), 100, $ry)
    $g.DrawString($row.saldo, $fRowVal, (New-Object System.Drawing.SolidBrush($ink)), 320, $ry)
    $g.DrawString($row.rend, $fRowVal, (New-Object System.Drawing.SolidBrush($verde)), 700, $ry)
    $ry += 80
}

$c.bmp.Save("$outDir\screenshot-2-projecao.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $c.bmp.Dispose()

# ---------- SCREENSHOT 3 : Compensa mais ----------
$c = New-Canvas 1080 1920 $paper
$g = $c.g
Draw-Brand $g 64 70

$fH3 = New-Object System.Drawing.Font("Georgia", 42, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Qual opcao`ncompensa mais?", $fH3, (New-Object System.Drawing.SolidBrush($ink)), 64, 190)
$fSub3 = New-Object System.Drawing.Font("Segoe UI", 24)
$g.DrawString("Digite quanto voce tem pra guardar e veja na hora`nquem paga mais, ja descontando o imposto.", $fSub3, (New-Object System.Drawing.SolidBrush($inkMute)), 64, 320)

# winner card (gold border)
$winnerBrush = New-Object System.Drawing.SolidBrush($white)
$winnerPen = New-Object System.Drawing.Pen($ouro, 3)
Draw-RoundRect $g $winnerPen $winnerBrush 64 440 952 680 24

$badgeBrush2 = New-Object System.Drawing.SolidBrush($ouro)
Draw-RoundRect $g $null $badgeBrush2 100 470 260 56 12
$fBadge = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$g.DrawString("MELHOR OPCAO", $fBadge, (New-Object System.Drawing.SolidBrush($white)), 122, 486)

$fWinnerName = New-Object System.Drawing.Font("Georgia", 40, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Nubank", $fWinnerName, (New-Object System.Drawing.SolidBrush($ink)), 100, 555)
$fWinnerProd = New-Object System.Drawing.Font("Segoe UI", 24)
$g.DrawString("LCI/LCA Nubank - 95% do CDI (isento de IR)", $fWinnerProd, (New-Object System.Drawing.SolidBrush($inkMute)), 100, 625)

$g.DrawLine((New-Object System.Drawing.Pen($border, 2)), 100, 700, 950, 700)

$fReceiptLabel = New-Object System.Drawing.Font("Segoe UI", 24)
$fReceiptVal = New-Object System.Drawing.Font("Consolas", 26, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Rendimento bruto", $fReceiptLabel, (New-Object System.Drawing.SolidBrush($ink)), 100, 740)
$g.DrawString("R`$ 1.570,11", $fReceiptVal, (New-Object System.Drawing.SolidBrush($ink)), 700, 738)
$g.DrawString("(-) Imposto de Renda (isento)", $fReceiptLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 100, 800)
$g.DrawString("R`$ 0,00", $fReceiptVal, (New-Object System.Drawing.SolidBrush($inkMute)), 780, 798)
$g.DrawLine((New-Object System.Drawing.Pen($border, 2)), 100, 870, 950, 870)
$fFinalLabel = New-Object System.Drawing.Font("Segoe UI", 22)
$g.DrawString("RENDIMENTO LIQUIDO", $fFinalLabel, (New-Object System.Drawing.SolidBrush($inkMute)), 100, 905)
$fFinalVal = New-Object System.Drawing.Font("Consolas", 40, [System.Drawing.FontStyle]::Bold)
$g.DrawString("R`$ 1.570,11", $fFinalVal, (New-Object System.Drawing.SolidBrush($verde)), 96, 940)

$fFinal2Label = New-Object System.Drawing.Font("Segoe UI", 20)
$g.DrawString("SALDO FINAL (APLICADO + RENDIMENTO)", $fFinal2Label, (New-Object System.Drawing.SolidBrush($inkMute)), 100, 1010)
$fFinal2Val = New-Object System.Drawing.Font("Consolas", 30, [System.Drawing.FontStyle]::Bold)
$g.DrawString("R`$ 51.570,11", $fFinal2Val, (New-Object System.Drawing.SolidBrush($ink)), 96, 1040)

$c.bmp.Save("$outDir\screenshot-3-comparar.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $c.bmp.Dispose()

# ---------- SCREENSHOT 4 : Combinar ----------
$c = New-Canvas 1080 1920 $paper
$g = $c.g
Draw-Brand $g 64 70

$fH4 = New-Object System.Drawing.Font("Georgia", 42, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Combine varios`ninvestimentos de uma vez", $fH4, (New-Object System.Drawing.SolidBrush($ink)), 64, 190)
$fSub4 = New-Object System.Drawing.Font("Segoe UI", 24)
$g.DrawString("Divida seu dinheiro entre bancos e corretoras`ndiferentes - ou deixe o app sugerir a melhor combinacao.", $fSub4, (New-Object System.Drawing.SolidBrush($inkMute)), 64, 320)

$cardBrush4 = New-Object System.Drawing.SolidBrush($white)
$cardPen4 = New-Object System.Drawing.Pen($border, 2)
Draw-RoundRect $g $cardPen4 $cardBrush4 64 460 952 260 24
$g.DrawString("BANCO / OPCAO", (New-Object System.Drawing.Font("Segoe UI", 18)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 495)
$g.DrawString("VALOR ALOCADO", (New-Object System.Drawing.Font("Segoe UI", 18)), (New-Object System.Drawing.SolidBrush($inkMute)), 700, 495)
$g.DrawLine((New-Object System.Drawing.Pen($border, 2)), 100, 535, 950, 535)
$g.DrawString("Nubank", (New-Object System.Drawing.Font("Georgia", 28, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($ink)), 100, 560)
$g.DrawString("LCI/LCA Nubank - 95% do CDI", (New-Object System.Drawing.Font("Segoe UI", 20)), (New-Object System.Drawing.SolidBrush($inkMute)), 100, 605)
$g.DrawString("R`$ 50.000,00", (New-Object System.Drawing.Font("Consolas", 28, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($ink)), 680, 575)
$g.DrawString("Alocado: R`$ 50.000,00  -  bate com o valor total (R`$ 50.000,00)", (New-Object System.Drawing.Font("Segoe UI", 18)), (New-Object System.Drawing.SolidBrush($verde)), 100, 665)

# total combinado card
$totalBrush = New-Object System.Drawing.SolidBrush($verdeLt)
$totalPen = New-Object System.Drawing.Pen($verde, 2)
Draw-RoundRect $g $totalPen $totalBrush 64 760 952 220 24
$g.DrawString("TOTAL COMBINADO", (New-Object System.Drawing.Font("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($verde)), 100, 800)
$g.DrawString("Rendimento bruto no periodo", (New-Object System.Drawing.Font("Segoe UI", 22)), (New-Object System.Drawing.SolidBrush($ink)), 100, 850)
$g.DrawString("R`$ 1.570,11", (New-Object System.Drawing.Font("Consolas", 40, [System.Drawing.FontStyle]::Bold)), (New-Object System.Drawing.SolidBrush($verde)), 96, 890)

$c.bmp.Save("$outDir\screenshot-4-combinar.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $c.bmp.Dispose()

# ---------- FEATURE GRAPHIC 1024x500 ----------
$c = New-Canvas 1024 500 $verde
$g = $c.g
# subtle darker green band
$bandBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#155A3E"))
$g.FillRectangle($bandBrush, 0, 380, 1024, 120)

# icon
$iconBrush = New-Object System.Drawing.SolidBrush($paper)
Draw-RoundRect $g $null $iconBrush 50 165 170 170 38
$fIconFG = New-Object System.Drawing.Font("Georgia", 62, [System.Drawing.FontStyle]::Bold)
$sf2 = New-Object System.Drawing.StringFormat
$sf2.Alignment = [System.Drawing.StringAlignment]::Center
$sf2.LineAlignment = [System.Drawing.StringAlignment]::Center
$rectIcon = New-Object System.Drawing.RectangleF(50, 165, 170, 170)
$g.DrawString("R`$", $fIconFG, (New-Object System.Drawing.SolidBrush($verde)), $rectIcon, $sf2)

$fFGTitle = New-Object System.Drawing.Font("Georgia", 44, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Caderneta de`nInvestimentos", $fFGTitle, (New-Object System.Drawing.SolidBrush($paper)), 260, 130)
$fFGSub = New-Object System.Drawing.Font("Segoe UI", 24)
$g.DrawString("Veja quanto seu dinheiro rende de verdade", $fFGSub, (New-Object System.Drawing.SolidBrush($paper)), 260, 300)

$c.bmp.Save("$outDir\feature-graphic.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $c.bmp.Dispose()

Write-Output "done"
