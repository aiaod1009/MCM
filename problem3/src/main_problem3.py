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


def main(robot_id: str, save_results: bool = True, log_to_file: bool = True,
         case_code: str = None):
    """
    问题3主程序

    参数:
        robot_id: 参赛队号
        save_results: 是否保存结果
        log_to_file: 是否保存日志到文件
        case_code: 测试案例编码（模拟器测试页面显示，用于表1填写与日志关联）

    返回:
        results: 完整结果字典
    """
    # 设置日志
    logger = None
    log_file = None
    robot = None
    final_results = None
    run_summary = {}
    results_dir_path = os.path.join(os.path.dirname(__file__), '..', 'results')

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

        print(f"日志保存路径: {os.path.relpath(log_file, os.path.join(os.path.dirname(__file__), '..'))}")
        print()

    try:
        print("\n" + "="*60)
        print("问题3：自动搜索定位并清除全向干扰源")
        print("="*60)
        print(f"参赛队号: {robot_id}")
        if case_code:
            print(f"测试案例编码: {case_code}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # 创建机器狗客户端
        print("连接模拟器...")
        robot = SimulatorClient(base_url="http://127.0.0.1:2026", robot_id=robot_id,
                                case_code=case_code)

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
                'average_clear_time': 0,
                'reviewed_channels': [],
                'recovered_channels': [],
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
                enable_2opt=True,  # 启用路径优化（2-opt + Or-opt），压缩巡游移动时间
                active_channels=phase1_result['active_channels'],
                scan_data=phase1_result['scan_data'],
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
        cleared_count = len(phase3_result['cleared'])
        failed_count = len(phase3_result['failed'])
        found_count = len(targets)

        # 竞赛口径：平均定位清除时间 = 本次测试总虚拟时间 ÷ 清除干扰源个数
        # （涵盖搜索、定位、清除、复核全过程的平均耗时）
        avg_locate_clear_time = (total_virtual_time / cleared_count) if cleared_count else 0.0

        print(f"\n总虚拟时间: {total_virtual_time:.1f} 秒 ({total_virtual_time/60:.1f} 分钟)")
        print(f"清除比例: {phase3_result['clearing_ratio']*100:.1f}%")
        print(f"成功清除: {cleared_count}/{found_count}")
        print(f"清除失败: {failed_count}")
        print(f"平均定位清除时间: {avg_locate_clear_time:.1f} 秒/个")

        # 汇总结果（program_runtime 需等 /exit 才能确定，稍后回填）
        final_results = {
            'robot_id': robot_id,
            'case_code': case_code,
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
                'cleared_count': cleared_count,
                'failed_count': failed_count,
                'clearing_ratio': phase3_result['clearing_ratio'],
                'average_clear_time': phase3_result['average_clear_time'],
                'total_time': phase3_result['total_time']
            },
            'summary': {
                'total_virtual_time': total_virtual_time,
                'clearing_ratio': phase3_result['clearing_ratio'],
                'cleared_count': cleared_count,
                'average_locate_clear_time': avg_locate_clear_time,
                'program_runtime_s': None,
                'success': phase3_result['clearing_ratio'] >= 1.0
            }
        }

        run_summary = {
            'total_virtual_time': total_virtual_time,
            'cleared_count': cleared_count,
            'found_count': found_count,
            'failed_count': failed_count,
            'clearing_ratio': phase3_result['clearing_ratio'],
            'average_locate_clear_time': avg_locate_clear_time,
        }

        if save_results:
            results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            result_file = os.path.join(results_dir, 'final_results.json')
            with open(result_file, 'w') as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
                print(f"\n最终结果已保存到: results/final_results.json")

        # ----------------------------------------------------------------
        # 收尾（表1 口径汇总、行为日志落盘）在 finally 中完成：
        # 程序运行时间要等 /exit 才能确定，故统一放到 /exit 之后输出。
        # ----------------------------------------------------------------

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
        # 清理：主动调用 /exit 结束测试（/exit 之后才能确定程序运行时间）
        print(f"\n清理资源...")
        if robot is not None:
            robot.exit()

        # ----------------------------------------------------------------
        # 表1 口径汇总 + 行为日志落盘
        # （程序运行时间、/exit 响应都要等 /exit 之后才有，故统一放在 finally）
        # ----------------------------------------------------------------
        try:
            program_runtime = robot.program_runtime if robot is not None else None

            if run_summary:
                print("\n" + "="*60)
                print("表1 问题3 测试结果（本次测试，可直接抄录）")
                print("="*60)
                print(f"  测试案例编码    : "
                      f"{case_code if case_code else '（未提供，请从模拟器测试页面抄录）'}")
                print(f"  清除干扰源个数  : {run_summary['cleared_count']}")
                print(f"  平均定位清除时间: {run_summary['average_locate_clear_time']:.1f} 秒")
                if program_runtime is not None:
                    print(f"  程序运行时间    : {program_runtime:.1f} 秒 "
                          f"({program_runtime/60:.2f} 分钟)")
                else:
                    print(f"  程序运行时间    : （未记录）")
                print("="*60)

            if robot is not None and save_results and os.path.exists(results_dir_path):
                stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                robot.save_log(os.path.join(results_dir_path, f'action_log_{stamp}.json'))
                robot.export_action_table(os.path.join(results_dir_path, f'action_table_{stamp}.csv'))

                # 回填程序运行时间并重写 final_results.json
                if final_results is not None:
                    final_results['summary']['program_runtime_s'] = program_runtime
                    with open(os.path.join(results_dir_path, 'final_results.json'), 'w') as f:
                        json.dump(final_results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  收尾记录失败: {e}")

        # 恢复stdout并关闭日志文件
        if logger:
            sys.stdout = logger.terminal
            logger.close()
            if log_file:
                print(f"\n日志已保存到: {log_file}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='问题3：自动搜索定位并清除全向干扰源')
    parser.add_argument('robot_id', type=str, nargs='?', help='参赛队号')
    parser.add_argument('--case-code', type=str, default=None,
                        help='测试案例编码（模拟器测试页面显示，用于表1填写与日志关联）')
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
    main(robot_id,
         save_results=not args.no_save,
         log_to_file=not args.no_log,
         case_code=args.case_code)
