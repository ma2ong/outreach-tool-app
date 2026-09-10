# Install the browser that reads directory pages a crawler cannot read (docs/124).
#
# browser-use pulls in about a hundred packages, among them openai 2.x, pydantic and an
# httpx fork. Installed beside the server they would replace dependencies uvicorn is
# running on, so it gets its own interpreter and is called as a subprocess.
#
# Python 3.12, not the 3.14 the server runs on: browser-use asks for >=3.11 and 3.12 is
# what its wheels are built and tested against.
#
#   .\scripts\setup_browser_harvest.ps1
$venv = "$env:USERPROFILE\.outreach-tool\bu-venv"
$python = "$venv\Scripts\python.exe"

if (Test-Path $python) {
    Write-Output "已安装：$venv"
} else {
    $py312 = (py -0p | Select-String -Pattern '3\.12').ToString()
    if (-not $py312) { Write-Error "没有找到 Python 3.12。先从 python.org 装一个 3.12"; exit 1 }
    Write-Output "正在创建 $venv ..."
    py -3.12 -m venv $venv
    if (-not (Test-Path $python)) { Write-Error "虚拟环境创建失败"; exit 1 }
    & $python -m pip install --quiet --upgrade pip
    Write-Output "正在安装 browser-use（约 100 个包，几分钟）..."
    & $python -m pip install --quiet browser-use
}

& $python -c "import browser_use; print('browser-use', getattr(browser_use,'__version__','installed'))"
if ($LASTEXITCODE -ne 0) { Write-Error "browser-use 装好了但导入失败"; exit 1 }

# It drives real Chrome, not a bundled Chromium: headless Chromium sits on Cloudflare's
# Turnstile forever, and real Chrome walks through it.
if (-not (Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe")) {
    Write-Warning "没找到 Chrome。浏览器采集需要真实的 Chrome，不是 Chromium"
}

$key = Join-Path (Split-Path -Parent $PSScriptRoot) "backend\deepseek_key.txt"
if (-not (Test-Path $key)) { Write-Warning "缺少 backend\deepseek_key.txt，浏览器采集需要它来读页面" }

Write-Output "好了。在「名录 / 竞品经销商页」抓不到公司时，会出现「用浏览器读这一页」的按钮。"
