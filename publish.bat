@echo off
chcp 65001 >nul
echo ========================================
echo   AI 日报 - 提交到公众号草稿箱
echo ========================================
echo.
echo 请选择发布模式：
echo  1 - AI 垂直日报
echo  2 - 全频道日报
echo  3 - 科技综合日报
echo.
set /p mode="请输入数字 (1/2/3): "

if "%mode%"=="1" set MODE=ai
if "%mode%"=="2" set MODE=all
if "%mode%"=="3" set MODE=tech
if "%MODE%"=="" set MODE=ai

echo.
echo 正在生成并发布 %MODE% 模式...
python main.py %MODE% --publish

echo.
if %errorlevel%==0 (
    echo ✅ 草稿已提交到公众号草稿箱，请手动发布
) else (
    echo ❌ 发布失败，请检查错误信息
)
echo.
pause
