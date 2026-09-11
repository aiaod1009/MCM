#!/bin/bash
# 问题3快速启动脚本（Linux/Mac）

echo "============================================================"
echo "问题3：自动搜索定位并清除全向干扰源"
echo "============================================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import numpy" &> /dev/null; then
    echo "安装依赖..."
    pip3 install -r requirements.txt
fi

echo ""
echo "请确保："
echo "  1. 模拟器已启动"
echo "  2. 已点击"开始测试""
echo ""

# 获取robot_id
read -p "请输入参赛队号（robot_id）: " ROBOT_ID

if [ -z "$ROBOT_ID" ]; then
    echo "错误：必须提供参赛队号"
    exit 1
fi

echo ""
echo "开始运行..."
echo "============================================================"
echo ""

# 运行主程序
cd src
python3 main_problem3.py "$ROBOT_ID"

echo ""
echo "============================================================"
echo "运行完成"
echo "============================================================"
