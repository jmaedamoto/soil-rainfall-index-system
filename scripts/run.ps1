# Windows用実行スクリプト
param(
    [string]$Mode = "dev",
    [int]$Port = 5000
)

# 仮想環境の有効化
.\venv\Scripts\Activate.ps1

switch ($Mode.ToLower()) {
    "dev" { 
        Write-Host "🔧 開発モードで起動中... Port: $Port" -ForegroundColor Cyan
        $env:FLASK_ENV = "development"
        $env:FLASK_DEBUG = "True"
        python app.py
    }
    "prod" { 
        Write-Host "🚀 本番モードで起動中... Port: $Port" -ForegroundColor Green
        gunicorn --bind "0.0.0.0:$Port" --workers 4 app:app
    }
    "test" { 
        Write-Host "🧪 テストを実行中..." -ForegroundColor Yellow
        pytest tests/ -v
    }
    default { 
        Write-Host "❌ 不明なモード: $Mode" -ForegroundColor Red
        Write-Host "使用可能なモード: dev, prod, test" -ForegroundColor White
    }
}
