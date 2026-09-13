@echo off
chcp 65001 > nul
echo ============================================================
echo            问题4测试脚本
echo ============================================================
echo.

echo [步骤1] 验证代码导入...
python test_import.py
echo.

if errorlevel 1 (
    echo ❌ 代码导入测试失败，请检查！
    pause
    exit /b 1
)

echo.
echo [步骤2] 准备运行问题4主程序...
echo 机器人ID: 202619020062
echo 模拟器URL: http://127.0.0.1:5000
echo.
echo 预计运行时间: 2-3小时（虚拟时间约114分钟）
echo.

set /p confirm="确认开始测试？(Y/N): "
if /i not "%confirm%"=="Y" (
    echo 测试取消
    pause
    exit /b 0
)

echo.
echo [步骤3] 开始运行...
echo ============================================================
echo.

cd src
python main_problem4.py --robot-id 202619020062

echo.
echo ============================================================
echo 测试完成！
echo.
echo 结果文件：results/problem4_results.json
echo.
echo 请检查最终统计信息，记录以下数据：
echo   1. 总虚拟时间
echo   2. 清除成功率
echo   3. 全向源/定向源数量
echo   4. 分类准确率
echo   5. 定位精度
echo ============================================================
echo.

pause
