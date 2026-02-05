# 土壌雨量指数プロジェクト用関数

function Activate-SoilEnv {
    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        .\venv\Scripts\Activate.ps1
        Write-Host "✅ 仮想環境が有効化されました" -ForegroundColor Green
    } else {
        Write-Host "❌ 仮想環境が見つかりません" -ForegroundColor Red
    }
}

function Start-SoilApp {
    param([string]$Mode = "dev")
    Activate-SoilEnv
    .\scripts\run.ps1 -Mode $Mode
}

function Test-SoilApp {
    Activate-SoilEnv
    pytest tests/ -v --cov=src
}

# エイリアス
Set-Alias soil-activate Activate-SoilEnv
Set-Alias soil-run Start-SoilApp
Set-Alias soil-test Test-SoilApp
