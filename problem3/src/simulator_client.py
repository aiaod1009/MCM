"""
模拟器通信客户端
与无线电干扰源环境模拟器进行HTTP通信
"""
import requests
import json
import time
from typing import Optional, Dict, Tuple, List
import numpy as np


class SimulatorClient:
    """模拟器客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:2026", robot_id: str = None):
        """
        初始化模拟器客户端

        Args:
            base_url: 模拟器服务地址
            robot_id: 机器狗ID（参赛队号）
        """
        self.base_url = base_url
        self.robot_id = robot_id

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
                    'virtual_time': self.virtual_time
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
                    'virtual_time': self.virtual_time
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

            if result.get('accepted') == True:
                print(f"\n✓ 测试结束")
                print(f"  虚拟时间: {self.virtual_time:.1f}秒 ({self.virtual_time/60:.1f}分钟)")
                print(f"  移动次数: {self.total_moves}")
                print(f"  切换频道: {self.total_switches}")
                print(f"  检测次数: {self.total_detections}")
                print(f"  清除数量: {self.total_clears}")
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
            'total_clears': self.total_clears
        }

    def save_log(self, filename: str):
        """保存日志到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'robot_id': self.robot_id,
                'statistics': self.get_statistics(),
                'actions': self.action_log
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ 日志已保存到: {filename}")
