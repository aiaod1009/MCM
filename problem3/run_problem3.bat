@echo off
REM 问题3快速启动脚本（Windows）

echo ============================================================
echo 问题3：自动搜索定位并清除全向干扰源
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查依赖
echo 检查依赖...
pip show numpy >nul 2>&1
if errorlevel 1 (
    echo 安装依赖...
    pip install -r requirements.txt
)

echo.
echo 请确保：
echo   1. 模拟器已启动
echo   2. 已点击"开始测试"
echo.

REM 获取robot_id
set /p ROBOT_ID="请输入参赛队号（robot_id）: "

if "%ROBOT_ID%"=="" (
    echo 错误：必须提供参赛队号
    pause
    exit /b 1
)

echo.
echo 开始运行...
echo ============================================================
echo.

REM 运行主程序
cd src
python main_problem3.py %ROBOT_ID%

echo.
echo ============================================================
echo 运行完成
echo ============================================================
pause
