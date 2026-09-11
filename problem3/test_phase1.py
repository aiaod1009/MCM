"""
测试阶段1：枚举频道扫描
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from simulator_client import SimulatorClient
from phase1_frequency_scan import FrequencyScan
import json


def main():
    """测试主函数"""
    print("="*60)
    print("问题3 - 阶段1 测试程序")
    print("="*60)

    # 配置参数
    BASE_URL = "http://127.0.0.1:2026"

    # 从命令行参数或输入获取robot_id
    if len(sys.argv) > 1:
        ROBOT_ID = sys.argv[1]
        print(f"参赛队号: {ROBOT_ID}")
    else:
        try:
            ROBOT_ID = input("请输入参赛队号（robot_id）: ").strip()
        except EOFError:
            ROBOT_ID = "202619020062"  # 默认队号
            print(f"使用默认队号: {ROBOT_ID}")

    if not ROBOT_ID:
        print("错误：参赛队号不能为空")
        return

    # 创建模拟器客户端
    client = SimulatorClient(base_url=BASE_URL, robot_id=ROBOT_ID)

    # 进入目标区域
    print("\n正在进入目标区域...")
    enter_result = client.enter()

    if enter_result.get('code') != 0:
        print(f"进入失败: {enter_result.get('message')}")
        return

    try:
        # 创建扫描器
        scanner = FrequencyScan(client)

        # 执行阶段1扫描（混合策略）
        scan_result = scanner.run(strategy='hybrid')

        # 保存扫描结果
        result_data = {
            'active_channels': scan_result.active_channels,
            'scan_data': {
                str(ch): [(pos.tolist(), angle) for pos, angle in data]
                for ch, data in scan_result.scan_data.items()
            },
            'statistics': {
                'n_channels': len(scan_result.active_channels),
                'n_detections': scan_result.n_detections,
                'n_switches': scan_result.n_switches,
                'scan_time': scan_result.scan_time,
                'virtual_time': client.virtual_time
            }
        }

        # 保存到文件
        os.makedirs('results', exist_ok=True)
        result_file = f'results/phase1_result_{ROBOT_ID}.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 扫描结果已保存到: {result_file}")

        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        print(f"发现干扰源数量: {len(scan_result.active_channels)}")
        print(f"有源频道: {scan_result.active_channels}")
        print(f"总检测次数: {scan_result.n_detections}")
        print(f"总切换次数: {scan_result.n_switches}")
        print(f"虚拟时间: {client.virtual_time:.1f}秒 ({client.virtual_time/60:.2f}分钟)")

        # 等待用户确认是否退出
        input("\n按回车键退出测试...")

    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 退出测试
        print("\n正在退出测试...")
        client.exit()

        # 保存日志
        os.makedirs('logs', exist_ok=True)
        log_file = f'logs/phase1_log_{ROBOT_ID}.json'
        client.save_log(log_file)


if __name__ == '__main__':
    main()
