"""
问题3主程序：自动搜索定位并清除全向干扰源

完整三阶段流程：
1. 阶段1：枚举频道扫描
2. 阶段2：逐源交会定位
3. 阶段3：巡游清除
"""

import sys
import os
import json
from datetime import datetime
import io

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from simulator_client import SimulatorClient
from phase1_frequency_scan import FrequencyScan
from phase2_localization import phase2_localization
from phase3_clearing import phase3_patrol_and_clear


class TeeLogger:
    """同时输出到终端和文件的日志类"""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()  # 实时写入

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def main(robot_id: str, save_results: bool = True, log_to_file: bool = True):
    """
    问题3主程序

    参数:
        robot_id: 参赛队号
        save_results: 是否保存结果
        log_to_file: 是否保存日志到文件

    返回:
        results: 完整结果字典
    """
    # 设置日志
    logger = None
    if log_to_file:
        # 创建test_logs目录
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'test_logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"创建日志目录: test_logs/")

        # 生成日志文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'test_log_{timestamp}.txt')

        # 重定向stdout到日志文件
        logger = TeeLogger(log_file)
        sys.stdout = logger

        print(f"日志保存路径: test_logs/test_log_{timestamp}.txt")
        print()

    try:
        print("\n" + "="*60)
        print("问题3：自动搜索定位并清除全向干扰源")
        print("="*60)
        print(f"参赛队号: {robot_id}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # 创建机器狗客户端
        print("连接模拟器...")
        robot = SimulatorClient(base_url="http://127.0.0.1:2026", robot_id=robot_id)

        # 进入目标区域
        print("正在进入目标区域...")
        enter_result = robot.enter()

        if enter_result.get('code') != 0:
            print(f"✗ 进入失败: {enter_result.get('message')}")
            return None

        print(f"✓ 成功进入目标区域")

        # ================================================================
        # 阶段1：枚举频道扫描
        # ================================================================
        print("\n" + "█"*60)
        print("█" + " "*58 + "█")
        print("█" + " "*20 + "阶段1：枚举频道扫描" + " "*18 + "█")
        print("█" + " "*58 + "█")
        print("█"*60 + "\n")

        # 使用FrequencyScan类
        scanner = FrequencyScan(robot)

        # 执行混合策略扫描（9个点全扫，确保高检测率）
        scan_result_obj = scanner.run(strategy='hybrid')

        # 转换为阶段2需要的格式
        phase1_result = {
            'active_channels': scan_result_obj.active_channels,
            'scan_data': {
                str(ch): [[list(pos), float(theta)] for pos, theta in data]
                for ch, data in scan_result_obj.scan_data.items()
            }
        }

        print(f"\n阶段1完成：")
        print(f"  发现 {len(phase1_result['active_channels'])} 个有源频道")
        print(f"  频道列表: {phase1_result['active_channels']}")

        # 检查是否发现频道
        if len(phase1_result['active_channels']) == 0:
            print(f"\n⚠️  警告：未发现任何有源频道！")
            print(f"  可能原因：")
            print(f"    1. 模拟器未正确响应（检查模拟器状态）")
            print(f"    2. 目标区域内确实无干扰源（检查测试场景）")
            print(f"    3. robot_id 不正确（检查参赛队号）")
            print(f"\n  程序将继续运行后续阶段（使用空数据）...")

        if save_results:
            # 确保results目录存在
            results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
                print(f"  创建结果目录: results/")

            result_file = os.path.join(results_dir, 'phase1_scan_result.json')
            with open(result_file, 'w') as f:
                json.dump(phase1_result, f, indent=2)
                print(f"  结果已保存到: results/phase1_scan_result.json")

        # ================================================================
        # 阶段2：逐源交会定位
        # ================================================================
        print("\n" + "█"*60)
        print("█" + " "*58 + "█")
        print("█" + " "*18 + "阶段2：逐源交会定位" + " "*18 + "█")
        print("█" + " "*58 + "█")
        print("█"*60 + "\n")

        targets = phase2_localization(
            phase1_result,
            enable_single_point=True,
            verbose=True
        )

        print(f"\n阶段2完成：")
        print(f"  成功定位 {len(targets)} 个干扰源")

        if len(targets) == 0:
            print(f"\n⚠️  警告：未定位到任何干扰源！")
            if len(phase1_result['active_channels']) == 0:
                print(f"  原因：阶段1未发现有源频道")
            else:
                print(f"  原因：所有频道定位失败（扇形无交集）")
            print(f"\n  程序将跳过阶段3...")

        if save_results:
            results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            result_file = os.path.join(results_dir, 'phase2_targets.json')
            with open(result_file, 'w') as f:
                json.dump([t.to_dict() for t in targets], f, indent=2)
                print(f"  结果已保存到: results/phase2_targets.json")

        # ================================================================
        # 阶段3：巡游清除
        # ================================================================

        if len(targets) == 0:
            print("\n⚠️  跳过阶段3：无目标可清除")

            # 创建空的阶段3结果
            phase3_result = {
                'cleared': [],
                'failed': [],
                'clear_times': {},
                'total_time': 0,
                'clearing_ratio': 0,
                'average_clear_time': 0
            }
        else:
            print("\n" + "█"*60)
            print("█" + " "*58 + "█")
            print("█" + " "*20 + "阶段3：巡游清除" + " "*22 + "█")
            print("█" + " "*58 + "█")
            print("█"*60 + "\n")

            phase3_result = phase3_patrol_and_clear(
                targets,
                robot,
                enable_2opt=True  # 启用2-opt路径优化，减少移动时间
            )

            print(f"\n阶段3完成：")
            print(f"  清除比例: {phase3_result['clearing_ratio']*100:.1f}%")
            print(f"  平均清除时间: {phase3_result['average_clear_time']:.1f} 秒")
            print(f"  总虚拟时间: {phase3_result['total_time']:.1f} 秒")

        # ================================================================
        # 最终统计
        # ================================================================
        print("\n" + "="*60)
        print("最终统计")
        print("="*60)

        total_virtual_time = robot.virtual_time  # 直接访问属性
        print(f"\n总虚拟时间: {total_virtual_time:.1f} 秒 ({total_virtual_time/60:.1f} 分钟)")
        print(f"清除比例: {phase3_result['clearing_ratio']*100:.1f}%")
        print(f"成功清除: {len(phase3_result['cleared'])}/{len(targets)}")
        print(f"清除失败: {len(phase3_result['failed'])}")

        # 汇总结果
        final_results = {
            'robot_id': robot_id,
            'timestamp': datetime.now().isoformat(),
            'phase1': {
                'active_channels': phase1_result['active_channels'],
                'total_channels': len(phase1_result['active_channels'])
            },
            'phase2': {
                'targets_count': len(targets),
                'targets': [t.to_dict() for t in targets]
            },
            'phase3': {
                'cleared_count': len(phase3_result['cleared']),
                'failed_count': len(phase3_result['failed']),
                'clearing_ratio': phase3_result['clearing_ratio'],
                'average_clear_time': phase3_result['average_clear_time'],
                'total_time': phase3_result['total_time']
            },
            'summary': {
                'total_virtual_time': total_virtual_time,
                'clearing_ratio': phase3_result['clearing_ratio'],
                'success': phase3_result['clearing_ratio'] >= 1.0
            }
        }

        if save_results:
            results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            result_file = os.path.join(results_dir, 'final_results.json')
            with open(result_file, 'w') as f:
                json.dump(final_results, f, indent=2)
                print(f"\n最终结果已保存到: results/final_results.json")

        # ================================================================
        # 完成
        # ================================================================
        print("\n" + "="*60)
        print("任务完成！")
        print("="*60)
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if phase3_result['clearing_ratio'] >= 1.0:
            print(f"\n✓ 成功！所有干扰源已清除！")
        else:
            print(f"\n⚠️  部分干扰源未清除：{len(phase3_result['failed'])}/{len(targets)}")

        print("="*60 + "\n")

        return final_results

    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断")
        return None

    except Exception as e:
        print(f"\n\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # 清理
        print(f"\n清理资源...")
        robot.exit()

        # 恢复stdout并关闭日志文件
        if logger:
            sys.stdout = logger.terminal
            logger.close()
            print(f"\n日志已保存到: test_logs/test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='问题3：自动搜索定位并清除全向干扰源')
    parser.add_argument('robot_id', type=str, nargs='?', help='参赛队号')
    parser.add_argument('--no-save', action='store_true', help='不保存结果')
    parser.add_argument('--no-log', action='store_true', help='不保存日志到文件')

    args = parser.parse_args()

    # 获取robot_id
    if args.robot_id:
        robot_id = args.robot_id
    else:
        robot_id = input("请输入参赛队号（robot_id）: ").strip()

    if not robot_id:
        print("错误：必须提供参赛队号")
        sys.exit(1)

    # 运行主程序
    main(robot_id, save_results=not args.no_save, log_to_file=not args.no_log)
