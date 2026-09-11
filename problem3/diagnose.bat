@echo off
REM 一键诊断脚本（Windows）

echo ============================================================
echo 问题3 - 一键诊断工具
echo ============================================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python未安装
    echo     请先安装Python 3.8+
    pause
    exit /b 1
) else (
    echo [√] Python已安装
)

REM 检查依赖
echo.
echo 检查Python依赖包...
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [X] numpy未安装
    echo     运行: pip install numpy
    set DEPS_OK=0
) else (
    echo [√] numpy已安装
)

python -c "import scipy" >nul 2>&1
if errorlevel 1 (
    echo [X] scipy未安装
    echo     运行: pip install scipy
    set DEPS_OK=0
) else (
    echo [√] scipy已安装
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [X] requests未安装
    echo     运行: pip install requests
    set DEPS_OK=0
) else (
    echo [√] requests已安装
)

REM 检查目录结构
echo.
echo 检查目录结构...
if exist "src\" (
    echo [√] src/ 目录存在
) else (
    echo [X] src/ 目录不存在
    set DEPS_OK=0
)

if exist "tests\" (
    echo [√] tests/ 目录存在
) else (
    echo [X] tests/ 目录不存在
    set DEPS_OK=0
)

if exist "tools\" (
    echo [√] tools/ 目录存在
) else (
    echo [X] tools/ 目录不存在
    set DEPS_OK=0
)

REM 创建results目录
if not exist "results\" (
    mkdir results
    echo [√] results/ 目录已创建
) else (
    echo [√] results/ 目录存在
)

REM 检查核心文件
echo.
echo 检查核心文件...
if exist "src\main_problem3.py" (
    echo [√] main_problem3.py 存在
) else (
    echo [X] main_problem3.py 不存在
    set DEPS_OK=0
)

if exist "src\phase1_frequency_scan.py" (
    echo [√] phase1_frequency_scan.py 存在
) else (
    echo [X] phase1_frequency_scan.py 不存在
    set DEPS_OK=0
)

if exist "src\phase2_localization.py" (
    echo [√] phase2_localization.py 存在
) else (
    echo [X] phase2_localization.py 不存在
    set DEPS_OK=0
)

if exist "src\phase3_clearing.py" (
    echo [√] phase3_clearing.py 存在
) else (
    echo [X] phase3_clearing.py 不存在
    set DEPS_OK=0
)

REM 运行单元测试
echo.
echo 运行单元测试...
echo.

echo 测试1: 几何算法
python tests\test_geometry_basic.py >nul 2>&1
if errorlevel 1 (
    echo [X] 几何算法测试失败
    set TEST_OK=0
) else (
    echo [√] 几何算法测试通过
)

echo 测试2: 阶段2定位
python tests\test_phase2.py >nul 2>&1
if errorlevel 1 (
    echo [X] 阶段2测试失败
    set TEST_OK=0
) else (
    echo [√] 阶段2测试通过
)

echo 测试3: 阶段3模块
python tests\test_phase3_modules.py >nul 2>&1
if errorlevel 1 (
    echo [X] 阶段3模块测试失败
    set TEST_OK=0
) else (
    echo [√] 阶段3模块测试通过
)

echo 测试4: 集成测试
python tests\test_integration.py >nul 2>&1
if errorlevel 1 (
    echo [X] 集成测试失败
    set TEST_OK=0
) else (
    echo [√] 集成测试通过
)

REM 总结
echo.
echo ============================================================
echo 诊断总结
echo ============================================================
echo.

if "%DEPS_OK%"=="0" (
    echo [!] 依赖检查未通过
    echo     请按照上面的提示安装缺失的依赖
    echo.
) else (
    echo [√] 所有依赖检查通过
    echo.
)

if "%TEST_OK%"=="0" (
    echo [!] 部分测试未通过
    echo     这可能不影响运行，但建议检查
    echo.
) else (
    echo [√] 所有测试通过
    echo.
)

echo 下一步：
echo   1. 确保模拟器已启动
echo   2. 点击"开始测试"按钮
echo   3. 运行连接测试：
echo      python tools\test_simulator_connection.py 你的robot_id
echo   4. 如果连接测试通过，运行主程序：
echo      cd src
echo      python main_problem3.py 你的robot_id
echo.

pause
