"""
模拟器通信客户端
与无线电干扰源环境模拟器进行HTTP通信
"""
import requests
import json
import time
from typing import Optional, Dict, Tuple, List
import numpy as np


def _json_default(obj):
    """json.dump 兜底序列化：把 numpy 标量/数组转成 Python 原生类型。

    位置参数在 measure/clear 入口已归一化为 float tuple，但 action_log 的
    'response' 字段来自模拟器响应，理论上不应含 numpy；此兜底用于防御
    任何残余的 numpy 标量，避免"Object of type ndarray is not JSON
    serializable"中断日志落盘。
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return str(obj)


class SimulatorClient:
    """模拟器客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:2026", robot_id: str = None,
                 case_code: str = None):
        """
        初始化模拟器客户端

        Args:
            base_url: 模拟器服务地址
            robot_id: 机器狗ID（参赛队号）
            case_code: 测试案例编码（测试页面显示，用于表1填写与日志关联）
        """
        self.base_url = base_url
        self.robot_id = robot_id
        self.case_code = case_code

        # 机器狗状态
        self.position = np.array([0.0, 0.0])  # 当前位置
        self.current_channel = 1  # 当前频道
        self.virtual_time = 0.0  # 虚拟世界时间

        # 统计信息
        self.total_moves = 0
        self.total_switches = 0
        self.total_detections = 0
        self.total_clears = 0

        # 请求ID计数
        self.request_counter = 0

        # 日志
        self.action_log = []

        # 程序运行时间（题面：/enter 到测试结束时刻的时长）
        self.enter_wall_time = None
        self.exit_wall_time = None
        self.program_runtime = None
        self.enter_response = None
        self.exit_response = None
        self.log_file = None

    def _get_request_id(self) -> str:
        """生成请求ID"""
        self.request_counter += 1
        return f"{self.robot_id}_{self.request_counter}_{int(time.time() * 1000)}"

    def _log_action(self, action: str, data: dict):
        """记录动作日志"""
        log_entry = {
            'timestamp': time.time(),
            'virtual_time': self.virtual_time,
            'action': action,
            'data': data
        }
        self.action_log.append(log_entry)

    def enter(self) -> dict:
        """
        进入目标区域，开始测试

        Returns:
            响应数据
        """
        url = f"{self.base_url}/enter"
        payload = {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": self._get_request_id()
        }

        try:
            print(f"  连接: {url}")
            print(f"  队号: {self.robot_id}")
            response = requests.post(url, json=payload, timeout=10)
            print(f"  状态码: {response.status_code}")

            result = response.json()
            print(f"  响应: {result}")

            if result.get('accepted') == True:
                # 记录程序运行时间起点（题面：成功调用 /enter 后开始计时）
                self.enter_wall_time = time.time()
                self.enter_response = result
                print(f"\n✓ 成功进入目标区域")
                print(f"  最大虚拟时间: {result.get('max_virtual_duration_s', 0)}秒")
                print(f"  最大真实时间: {result.get('max_real_duration_s', 0)}秒")
                print(f"  剩余真实时间: {result.get('remaining_real_duration_s', 0)}秒")
                self._log_action('enter', result)
                result['code'] = 0  # 兼容处理
            else:
                print(f"\n✗ 进入失败")
                print(f"  响应: {result}")
                result['code'] = -1

            return result
        except requests.exceptions.ConnectionError as e:
            print(f"\n✗ 连接失败: 无法连接到模拟器")
            print(f"  请检查:")
            print(f"    1. 模拟器是否已启动")
            print(f"    2. 地址是否正确: {self.base_url}")
            print(f"    3. 是否已登录模拟器")
            print(f"    4. 是否已开始测试（倒计时结束）")
            return {'code': -1, 'message': f'连接失败: {str(e)}'}
        except Exception as e:
            print(f"\n✗ 进入失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'code': -1, 'message': str(e)}

    def measure(self, position: Tuple[float, float], channel: int) -> dict:
        """
        移动到指定位置并检测指定频道

        Args:
            position: 目标位置 (x, y)
            channel: 频道号 1-20

        Returns:
            检测结果字典:
            {
                'code': 0,
                'result': 'no_signal' | 'near' | 'direction',
                'svd_deg': float (仅当result='direction'时)
            }
        """
        url = f"{self.base_url}/measure"
        # 归一化位置：调用方可能传 np.ndarray/tuple/list，统一转 float tuple，
        # 避免后续行为日志 JSON 序列化时遇到 ndarray 而报错。
        position = tuple(float(v) for v in position)
        payload = {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": self._get_request_id(),
            "position": {"x": float(position[0]), "y": float(position[1])},
            "channel": channel
        }

        try:
            # 计算移动距离和时间
            old_position = self.position.copy()
            new_position = np.array(position)
            move_distance = np.linalg.norm(new_position - old_position)
            move_time = move_distance / 5.0  # 速度5m/s

            # 计算切换频道时间
            switch_time = 1.0 if channel != self.current_channel else 0.0

            # 检测时间
            detection_time = 5.0

            # 总耗时
            total_time = move_time + switch_time + detection_time

            response = requests.post(url, json=payload, timeout=15)
            result = response.json()

            # 检查是否被接受
            if result.get('accepted') == True:
                # 从响应中获取虚拟时间
                self.virtual_time = result.get('virtual_time_s', self.virtual_time)

                # 更新状态
                self.position = new_position
                self.current_channel = channel

                if move_distance > 0:
                    self.total_moves += 1
                if switch_time > 0:
                    self.total_switches += 1
                self.total_detections += 1

                # 解析结果
                measure_result = result.get('measure_result', 'no_signal')
                svd_deg = result.get('svd_deg')

                self._log_action('measure', {
                    'position': position,
                    'channel': channel,
                    'result': measure_result,
                    'svd_deg': svd_deg,
                    'move_distance_m': float(move_distance),
                    'move_time_s': float(move_time),
                    'switched': bool(switch_time > 0),
                    'switch_time_s': float(switch_time),
                    'detect_time_s': float(detection_time),
                    'virtual_time': self.virtual_time,
                    'response': dict(result)
                })

                # 兼容返回格式
                result['code'] = 0
                result['result'] = measure_result
            else:
                result['code'] = -1
                result['result'] = 'error'

            return result

        except Exception as e:
            print(f"✗ 检测失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    def clear(self, position: Tuple[float, float], channel: int) -> dict:
        """
        移动到指定位置并清除指定频道的干扰源

        Args:
            position: 目标位置 (x, y)
            channel: 频道号 1-20

        Returns:
            清除结果字典:
            {
                'code': 0,
                'result': 'no_target_in_range' | 'success'
            }
        """
        url = f"{self.base_url}/clear"
        # 归一化位置：调用方可能传 np.ndarray/tuple/list，统一转 float tuple，
        # 避免后续行为日志 JSON 序列化时遇到 ndarray 而报错。
        position = tuple(float(v) for v in position)
        payload = {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": self._get_request_id(),
            "position": {"x": float(position[0]), "y": float(position[1])},
            "channel": channel
        }

        try:
            # 计算移动距离和时间
            old_position = self.position.copy()
            new_position = np.array(position)
            move_distance = np.linalg.norm(new_position - old_position)
            move_time = move_distance / 5.0

            response = requests.post(url, json=payload, timeout=15)
            result = response.json()

            if result.get('accepted') == True:
                # 从响应中获取虚拟时间
                self.virtual_time = result.get('virtual_time_s', self.virtual_time)

                clear_result = result.get('clear_result', 'no_target_in_range')

                # 更新状态
                self.position = new_position

                if move_distance > 0:
                    self.total_moves += 1
                if clear_result == 'success':
                    self.total_clears += 1

                self._log_action('clear', {
                    'position': position,
                    'channel': channel,
                    'result': clear_result,
                    'move_distance_m': float(move_distance),
                    'move_time_s': float(move_time),
                    # 题面：先用光学精确定位耗时3秒；若发现目标再激光清除耗时2秒
                    'locate_time_s': 3.0,
                    'clear_time_s': 2.0 if clear_result == 'success' else 0.0,
                    'virtual_time': self.virtual_time,
                    'response': dict(result)
                })

                # 兼容返回格式
                result['code'] = 0
                result['result'] = clear_result
            else:
                result['code'] = -1
                result['result'] = 'error'

            return result

        except Exception as e:
            print(f"✗ 清除失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    def exit(self) -> dict:
        """
        结束测试

        Returns:
            响应数据
        """
        url = f"{self.base_url}/exit"
        payload = {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": self._get_request_id()
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            # 记录程序运行时间终点（题面：/enter 与测试结束时刻之间的时长）
            self.exit_wall_time = time.time()
            if self.enter_wall_time is not None:
                self.program_runtime = self.exit_wall_time - self.enter_wall_time
            self.exit_response = result

            if result.get('accepted') == True:
                print(f"\n✓ 测试结束")
                print(f"  虚拟时间: {self.virtual_time:.1f}秒 ({self.virtual_time/60:.1f}分钟)")
                print(f"  移动次数: {self.total_moves}")
                print(f"  切换频道: {self.total_switches}")
                print(f"  检测次数: {self.total_detections}")
                print(f"  清除数量: {self.total_clears}")
                if self.program_runtime is not None:
                    print(f"  程序运行时间: {self.program_runtime:.1f}秒 ({self.program_runtime/60:.2f}分钟)")
                if self.case_code:
                    print(f"  测试案例编码: {self.case_code}")
                self._log_action('exit', result)
                result['code'] = 0
            else:
                result['code'] = -1

            return result

        except Exception as e:
            print(f"✗ 退出失败: {str(e)}")
            return {'code': -1, 'message': str(e)}

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'virtual_time': self.virtual_time,
            'position': self.position.tolist(),
            'current_channel': self.current_channel,
            'total_moves': self.total_moves,
            'total_switches': self.total_switches,
            'total_detections': self.total_detections,
            'total_clears': self.total_clears,
            'program_runtime_s': self.program_runtime,
            'case_code': self.case_code
        }

    def save_log(self, filename: str):
        """
        保存完整行为日志到文件。

        题面（附件1 4.6）要求"机器狗程序应自行记录测试过程中的指令序列、
        响应信息等内容"，故日志包含：机器人 ID、测试案例编码、程序运行时间、
        /enter 与 /exit 的完整响应，以及逐条指令（含位置/频道参数、移动距离、
        移动耗时、切换耗时、检测/清除耗时、虚拟世界时刻、模拟器响应）。
        """
        payload = {
            'robot_id': self.robot_id,
            'case_code': self.case_code,
            'program_runtime_s': self.program_runtime,
            'statistics': self.get_statistics(),
            'enter_response': self.enter_response,
            'exit_response': self.exit_response,
            'actions': self.action_log
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False,
                      default=_json_default)
        self.log_file = filename
        print(f"✓ 行为日志已保存到: {filename}")

    def export_action_table(self, filename: str):
        """
        按附件1 表2 的格式导出"指令序列与耗时"表（CSV）。

        列：序号 / 指令 / 位置参数 / 频道参数 / 移动距离 / 移动耗时 /
            切换频道耗时 / 检测或清除耗时 / 指令总耗时 / 虚拟世界时刻
        """
        import csv

        rows = []
        seq = 0

        for entry in self.action_log:
            act = entry.get('action')
            d = entry.get('data', {}) or {}
            vt = round(float(entry.get('virtual_time', 0.0)), 3)

            if act == 'enter':
                seq += 1
                rows.append([seq, 'POST /enter', '-', '-', 0.0, 0.0, 0.0, 0.0, 0.0, vt])

            elif act == 'measure':
                seq += 1
                pos = d.get('position', [0, 0])
                mv = float(d.get('move_time_s', 0.0))
                sw = float(d.get('switch_time_s', 0.0))
                dt = float(d.get('detect_time_s', 5.0))
                rows.append([
                    seq, 'POST /measure', f"({pos[0]:.3f}, {pos[1]:.3f})", d.get('channel'),
                    round(float(d.get('move_distance_m', 0.0)), 3),
                    round(mv, 3), round(sw, 3), round(dt, 3), round(mv + sw + dt, 3), vt
                ])

            elif act == 'clear':
                seq += 1
                pos = d.get('position', [0, 0])
                mv = float(d.get('move_time_s', 0.0))
                lo = float(d.get('locate_time_s', 3.0))
                cl = float(d.get('clear_time_s', 0.0))
                rows.append([
                    seq, 'POST /clear', f"({pos[0]:.3f}, {pos[1]:.3f})", d.get('channel'),
                    round(float(d.get('move_distance_m', 0.0)), 3),
                    round(mv, 3), 0.0, round(lo + cl, 3), round(mv + lo + cl, 3), vt
                ])

            elif act == 'exit':
                seq += 1
                rows.append([seq, 'POST /exit', '-', '-', 0.0, 0.0, 0.0, 0.0, 0.0, vt])

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['序号', '指令', '位置参数', '频道参数', '移动距离(米)', '移动耗时(秒)',
                             '切换频道耗时(秒)', '检测/清除耗时(秒)', '指令总耗时(秒)', '虚拟世界时刻(秒)'])
            writer.writerows(rows)

        print(f"✓ 指令序列表已导出: {filename}（共 {len(rows)} 条指令）")
