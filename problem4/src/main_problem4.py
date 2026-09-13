# -*- coding: utf-8 -*-
"""
问题4主程序：全向+定向混合干扰源清除

基于问题3的成功经验，增加：
1. 全向/定向分类判断
2. 楔形交会定位（定向源）
3. 补充采样策略
"""
import sys
import os
import time
import json
from datetime import datetime

# 添加问题3的路径
# 路径结构：problem4/src/main_problem4.py
# 目标路径：B题/问题3/MCM/problem3/src
current_file = os.path.abspath(__file__)  # .../problem4/src/main_problem4.py
src_dir = os.path.dirname(current_file)  # .../problem4/src
problem4_root = os.path.dirname(src_dir)  # .../problem4
mcm_dir = os.path.dirname(problem4_root)  # .../MCM
problem4_dir = os.path.dirname(mcm_dir)  # .../问题4
b_problem_dir = os.path.dirname(problem4_dir)  # .../B题
problem3_src_path = os.path.join(b_problem_dir, '问题3', 'MCM', 'problem3', 'src')

if os.path.exists(problem3_src_path):
    sys.path.insert(0, problem3_src_path)
else:
    print(f"[ERROR] problem3 path not found: {problem3_src_path}")
    sys.exit(1)


class TeeLogger:
    """同时输出到终端和文件的日志类（复用问题3）"""
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

# 问题4模块
from phase1_enhanced_scan import EnhancedScanner
from phase2_classification_localization import ClassificationLocalizer

# 复用问题3的阶段3模块
try:
    from phase3_clearing import phase3_patrol_and_clear
    from simulator_client import SimulatorClient
except ImportError as e:
    print(f"Error: Cannot import from problem3: {e}")
    sys.exit(1)


class ClearingPhaseWrapper:
    """阶段3清除的包装类（适配问题3的函数接口）"""

    def __init__(self, robot_id: str, base_url: str = "http://127.0.0.1:2026"):
        self.robot_id = robot_id
        self.base_url = base_url
        self.client = SimulatorClient(base_url=base_url, robot_id=robot_id)

    def patrol_and_clear(self, targets):
        """调用问题3的phase3_patrol_and_clear函数"""
        return phase3_patrol_and_clear(targets, self.client, enable_2opt=False)


class Problem4Solver:
    """问题4求解器"""

    def __init__(self, robot_id: str, base_url: str = "http://127.0.0.1:2026"):
        self.robot_id = robot_id
        self.base_url = base_url

        # 使用同一个client实例，让阶段1和阶段3共享状态
        self.client = SimulatorClient(base_url=base_url, robot_id=robot_id)

        # 初始化各阶段（传入共享的client）
        self.scanner = EnhancedScanner(robot_id, base_url)
        # 注意：scanner内部也会创建自己的client，所以要在扫描后更新主client的状态
        self.localizer = ClassificationLocalizer()
        self.clearer = ClearingPhaseWrapper(robot_id, base_url)

        # 结果存储
        self.results = {
            'robot_id': robot_id,
            'timestamp': None,
            'phase1': None,
            'phase2': None,
            'phase3': None,
            'summary': None
        }

    def solve(self):
        """
        完整求解流程

        三阶段增强版：
        1. 增强扫描（基础+补充）
        2. 分类定位（全向/定向判断+相应算法）
        3. 巡游清除（继承问题3）
        """
        print("\n" + "="*80)
        print(" "*20 + "问题4：全向+定向混合干扰源清除")
        print("="*80)
        print(f"参赛队号：{self.robot_id}")
        print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        start_time = time.time()

        try:
            # 调用enter进入测试区域
            print("\n正在进入测试区域...")
            enter_result = self.client.enter()
            if enter_result.get('code') != 0:
                print(f"❌ 进入失败: {enter_result.get('message', '未知错误')}")
                return None
            print("✅ 成功进入测试区域")

            # 阶段1：增强扫描（内部会创建自己的client）
            scan_result = self.scanner.scan_with_supplementary()

            # 同步scanner的client统计数据到主client
            if hasattr(self.scanner, 'client'):
                self.client.virtual_time = self.scanner.client.virtual_time
                self.client.position = self.scanner.client.position
                self.client.current_channel = self.scanner.client.current_channel
                self.client.total_moves = self.scanner.client.total_moves
                self.client.total_switches = self.scanner.client.total_switches
                self.client.total_detections = self.scanner.client.total_detections
                self.client.total_clears = self.scanner.client.total_clears

            self.results['phase1'] = {
                'active_channels': scan_result['active_channels'],
                'total_channels': len(scan_result['active_channels']),
                'supplementary_channels': list(scan_result['supplementary_data'].keys())
            }

            # 阶段2：分类定位
            targets = self.localizer.localize_all(scan_result)
            self.results['phase2'] = {
                'targets_count': len(targets),
                'targets': targets
            }

            # 阶段3：巡游清除（Target对象已经是问题3兼容格式）
            clearing_result = self.clearer.patrol_and_clear(targets)
            self.results['phase3'] = clearing_result

            # 同步clearer的client统计数据到主client
            if hasattr(self.clearer, 'client'):
                self.client.virtual_time = self.clearer.client.virtual_time
                self.client.position = self.clearer.client.position
                self.client.current_channel = self.clearer.client.current_channel
                self.client.total_moves = self.clearer.client.total_moves
                self.client.total_switches = self.clearer.client.total_switches
                self.client.total_detections = self.clearer.client.total_detections
                self.client.total_clears = self.clearer.client.total_clears

            # 汇总
            total_time = time.time() - start_time
            self.results['timestamp'] = datetime.now().isoformat()
            self.results['summary'] = {
                'total_virtual_time': self.client.virtual_time,  # 使用实际统计的虚拟时间
                'clearing_ratio': clearing_result['clearing_ratio'],
                'success': len(clearing_result['cleared']) == len(targets)
            }

            # 打印最终结果
            self._print_final_results()

            # 保存结果
            self._save_results()

            # 调用exit退出测试（使用主client）
            print("\n正在退出测试...")
            exit_result = self.client.exit()
            if exit_result.get('code') == 0:
                print("✅ 成功退出测试")
            else:
                print(f"⚠️  退出失败: {exit_result.get('message', '未知错误')}")

            return self.results

        except Exception as e:
            print(f"\n❌ 错误：{e}")
            import traceback
            traceback.print_exc()
            return None

    def _print_final_results(self):
        """打印最终结果"""
        print("\n" + "="*80)
        print(" "*30 + "最终统计")
        print("="*80)

        summary = self.results['summary']
        phase2 = self.results['phase2']
        phase3 = self.results['phase3']

        print(f"\n总虚拟时间: {summary['total_virtual_time']:.1f} 秒 "
              f"({summary['total_virtual_time']/60:.1f} 分钟)")
        print(f"清除比例: {summary['clearing_ratio']*100:.1f}%")
        print(f"成功清除: {len(phase3['cleared'])}/{phase2['targets_count']}")

        if len(phase3['failed']) > 0:
            print(f"清除失败: {len(phase3['failed'])}")

        print(f"\n动作统计：")
        print(f"  移动次数: {self.client.total_moves}")
        print(f"  切换频道: {self.client.total_switches}")
        print(f"  检测次数: {self.client.total_detections}")
        print(f"  清除次数: {self.client.total_clears}")

        if summary['success']:
            print("\n✅ 任务完成！所有干扰源已清除")
        else:
            print(f"\n⚠️  部分干扰源未清除：{len(phase3['failed'])}/{phase2['targets_count']}")

        print("="*80)

    def _save_results(self):
        """保存结果到JSON文件"""
        # 创建results目录
        results_dir = os.path.join(os.path.dirname(__file__), '../results')
        os.makedirs(results_dir, exist_ok=True)

        # 转换Target对象为可序列化的dict
        serializable_results = self.results.copy()

        # 转换phase2的targets列表
        if 'phase2' in serializable_results and 'targets' in serializable_results['phase2']:
            serializable_results['phase2']['targets'] = [
                {
                    'channel_id': t.channel_id,
                    'center': t.center.tolist() if hasattr(t.center, 'tolist') else list(t.center),
                    'diameter': float(t.diameter),
                    'confidence': float(t.confidence),
                    'source_type': getattr(t, 'source_type', 'unknown'),
                    'classification_confidence': getattr(t, 'classification_confidence', 0.0),
                    'method': getattr(t, 'method', 'unknown')
                }
                for t in serializable_results['phase2']['targets']
            ]

        # 转换phase3的cleared和failed列表
        if 'phase3' in serializable_results:
            if 'cleared' in serializable_results['phase3']:
                serializable_results['phase3']['cleared'] = [
                    {
                        'channel_id': t.channel_id,
                        'center': t.center.tolist() if hasattr(t.center, 'tolist') else list(t.center),
                        'diameter': float(t.diameter),
                        'confidence': float(t.confidence)
                    }
                    for t in serializable_results['phase3']['cleared']
                ]
            if 'failed' in serializable_results['phase3']:
                serializable_results['phase3']['failed'] = [
                    {
                        'channel_id': t.channel_id,
                        'center': t.center.tolist() if hasattr(t.center, 'tolist') else list(t.center),
                        'diameter': float(t.diameter),
                        'confidence': float(t.confidence)
                    }
                    for t in serializable_results['phase3']['failed']
                ]

        # 保存完整结果
        result_file = os.path.join(results_dir, 'problem4_results.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {result_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='问题4：全向+定向混合干扰源清除')
    parser.add_argument('--robot-id', type=str, default='202619020062',
                       help='机器人ID')
    parser.add_argument('--url', type=str, default='http://127.0.0.1:2026',
                       help='模拟器URL')
    parser.add_argument('--no-log', action='store_true',
                       help='不保存日志到文件')

    args = parser.parse_args()

    # 设置日志
    logger = None
    if not args.no_log:
        # 创建test_logs目录
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'test_logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 生成日志文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'test_log_{timestamp}.txt')

        # 重定向stdout到日志文件
        logger = TeeLogger(log_file)
        sys.stdout = logger

        print(f"日志保存路径: test_logs/test_log_{timestamp}.txt")
        print()

    try:
        # 创建求解器
        solver = Problem4Solver(robot_id=args.robot_id, base_url=args.url)

        # 求解
        result = solver.solve()

        if result:
            print("\n✅ 问题4求解完成！")
            return 0
        else:
            print("\n❌ 问题4求解失败")
            return 1

    finally:
        # 恢复stdout并关闭日志文件
        if logger:
            sys.stdout = logger.terminal
            logger.close()
            print(f"\n日志已保存到: test_logs/test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
