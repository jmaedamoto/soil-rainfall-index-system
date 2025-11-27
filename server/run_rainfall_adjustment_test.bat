@echo off
echo ========================================
echo 雨量調整機能 統合テスト実行
echo ========================================
echo.

cd /d %~dp0

echo Pythonバージョン確認...
python --version
echo.

echo テスト実行中...
python tests\test_rainfall_adjustment_integration.py

echo.
echo テスト完了
pause
