# Windows用セットアップスクリプト
param(
    [switch]$Clean,
    [switch]$Dev
)

if ($Clean) {
    Write-Host "🧹 クリーンセットアップを実行中..." -ForegroundColor Yellow
    Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "data\cache\*" -Force -ErrorAction SilentlyContinue
}

Write-Host "🚀 Python環境をセットアップ中..." -ForegroundColor Cyan
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

if ($Dev) {
    Write-Host "🔧 開発用ツールをインストール中..." -ForegroundColor Cyan
    pip install -e .
}

Write-Host "✅ セットアップが完了しました!" -ForegroundColor Green
