"""
按竞赛官方口径统计一次模拟器运行的结果（表1 用）。

题面定义（B题.md 问题3）：
    被清除干扰源个数的比例 = 被清除干扰源的个数 / 干扰源总数
    平均定位清除时间       = 定位清除总时间 / 被清除干扰源的个数
    （定位清除总时间 = 全部虚拟时间，含移动/切换频道/检测/精确定位/清除）

注意：脚本内部 phase3 打印的"平均清除时间"是各目标用时的算术平均，
      不是官方口径，不要直接填表。

用法:
    python tools/report_run_metrics.py test_logs/test_log_20260912_233337.txt [干扰源总数]
"""
import json
import os
import re
import sys

SPEED = 5.0          # 题面: 移动速度 5 m/s
T_SWITCH = 1.0       # 题面: 频道切换 1 s
T_MEASURE = 5.0      # 题面: 一次检测 5 s
T_CLEAR_OK = 5.0     # 题面: 清除成功 3+2 s
T_CLEAR_FAIL = 3.0   # 题面: 精确定位未发现 3 s


def parse_log(path):
    txt = open(path, encoding='utf-8', errors='ignore').read()
    out = {}

    def grab(pattern, cast=float, default=None, last=False):
        found = re.findall(pattern, txt)
        if not found:
            return default
        return cast(found[-1] if last else found[0])

    # 阶段3 与 最终统计 都会打印"总虚拟时间"，只有末次(整轮总时)才有效
    out['总虚拟时间'] = grab(r'总虚拟时间:\s*([0-9.]+)\s*秒', last=True)
    out['阶段1虚拟时间'] = grab(r'阶段1 扫描完成.*?虚拟时间:\s*([0-9.]+)\s*秒', default=None)
    if out['阶段1虚拟时间'] is None:
        out['阶段1虚拟时间'] = grab(r'虚拟时间:\s*([0-9.]+)\s*秒\s*\(37', default=None)
    out['阶段3虚拟时间'] = grab(r'总虚拟时间:\s*([0-9.]+)\s*秒\s*\(80')
    # 阶段1 内部也会打印"检测次数/频道切换次数"，取末次(最终统计)
    out['移动次数'] = grab(r'移动次数:\s*([0-9]+)', int, last=True)
    out['切换频道'] = grab(r'切换频道:\s*([0-9]+)', int, last=True)
    out['检测次数'] = grab(r'检测次数:\s*([0-9]+)', int, last=True)
    out['清除数量'] = grab(r'清除数量:\s*([0-9]+)', int, last=True)

    m = re.search(r'发现\s*([0-9]+)\s*个有源频道', txt)
    out['发现频道数'] = int(m.group(1)) if m else None

    m = re.search(r'阶段2完成：成功定位\s*([0-9]+)\s*个', txt)
    out['定位成功数'] = int(m.group(1)) if m else None

    m = re.search(r'成功清除:\s*([0-9]+)/([0-9]+)', txt)
    if m:
        out['清除成功数'] = int(m.group(1))
        out['清除分母'] = int(m.group(2))

    # 起始/结束时间
    m = re.search(r'开始时间:\s*(\S+ \S+)', txt)
    m2 = re.search(r'结束时间:\s*(\S+ \S+)', txt)
    out['开始时间'] = m.group(1) if m else None
    out['结束时间'] = m2.group(1) if m2 else None

    # 每个目标的清除用时
    times = re.findall(r'用时:\s*([0-9.]+)\s*秒', txt)
    out['各目标用时'] = [float(x) for x in times]

    # 通道明细
    out['清除明细'] = re.findall(r'✓ 频道\s*([0-9]+):\s*([0-9.]+)秒', txt)

    # 按"清除目标：频道 N"切段，逐段判断是否重试/精修（避免跨段误匹配）
    heads = list(re.finditer(r'清除目标：频道\s*([0-9]+)', txt))
    retry, refine = [], []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(txt)
        seg = txt[h.end():end]
        if '✗ 清除失败' in seg:
            retry.append(h.group(1))
        if '启动精修' in seg:
            refine.append(h.group(1))
    out['重试目标'] = retry
    out['精修目标'] = refine

    # ---- 程序运行时间（题面：/enter 到测试结束时刻的时长）----
    out['程序运行时间'] = grab(r'程序运行时间:\s*([0-9.]+)\s*秒', default=None, last=True)

    # ---- 测试案例编码（模拟器测试页面显示，程序运行时通过 --case-code 传入）----
    codes = re.findall(r'测试案例编码\s*[:：]\s*(\S+)', txt)
    out['案例编码'] = codes[-1] if codes else None
    if out['案例编码'] and out['案例编码'].startswith('（'):
        out['案例编码'] = None

    # ---- 程序自己打印的"表1 口径"块（最权威，直接抄）----
    blk = {}
    m = re.search(r'表1 问题3 测试结果.*?\n(.*?)={10,}', txt, re.S)
    if m:
        body = m.group(1)
        for key, pat in [
            ('清除干扰源个数', r'清除干扰源个数\s*[:：]\s*([0-9]+)'),
            ('平均定位清除时间', r'平均定位清除时间\s*[:：]\s*([0-9.]+)'),
            ('程序运行时间', r'程序运行时间\s*[:：]\s*([0-9.]+)'),
        ]:
            mm = re.search(pat, body)
            if mm:
                blk[key] = mm.group(1)
        cm = re.search(r'测试案例编码\s*[:：]\s*(\S+)', body)
        if cm and not cm.group(1).startswith('（'):
            blk['测试案例编码'] = cm.group(1)
    out['表1块'] = blk

    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    total_sources = int(sys.argv[2]) if len(sys.argv) > 2 else None

    d = parse_log(path)
    n_clear = d.get('清除成功数') or d.get('清除数量') or 0
    total_v = d.get('总虚拟时间') or 0.0

    print('=' * 62)
    print(f'运行结果统计（官方口径）  {os.path.basename(path)}')
    print('=' * 62)
    print(f"发现频道数        : {d.get('发现频道数')}")
    print(f"定位成功数        : {d.get('定位成功数')}")
    print(f"清除成功数        : {n_clear}")
    if total_sources:
        print(f"干扰源总数(真值)  : {total_sources}   [来自模拟器演练测试界面]")
        print(f"清除比例          : {n_clear / total_sources * 100:.1f}%"
              f"   ({n_clear}/{total_sources})")
    else:
        print("清除比例          : 需提供干扰源总数（演练测试完成后模拟器界面显示）")
    print()
    print(f"总虚拟时间        : {total_v:.1f} 秒 ({total_v/60:.1f} 分钟)")
    if n_clear:
        print(f"平均定位清除时间  : {total_v / n_clear:.1f} 秒   <- 表1 填这个")
    avg_internal = (sum(d['各目标用时']) / len(d['各目标用时'])
                    if d['各目标用时'] else 0)
    print(f"（脚本内部平均清除时间 {avg_internal:.1f} 秒 = 各目标用时算术平均，非官方口径）")
    print()
    print('--- 时间构成（题面参数推算）---')
    p1 = d.get('阶段1虚拟时间') or 0
    p3 = d.get('阶段3虚拟时间') or 0
    mea = d.get('检测次数') or 0
    swi = d.get('切换频道') or 0
    print(f"  阶段1(扫描)      : {p1:.1f} 秒")
    print(f"  阶段3(清除+验证) : {p3:.1f} 秒")
    print(f"  检测总耗时       : {mea} x {T_MEASURE:.0f} = {mea * T_MEASURE:.0f} 秒")
    print(f"  切换总耗时       : {swi} x {T_SWITCH:.0f} = {swi * T_SWITCH:.0f} 秒")
    print(f"  剩余(移动+清除)  : {total_v - mea * T_MEASURE - swi * T_SWITCH:.0f} 秒")
    print()
    if d.get('重试目标'):
        retry = sorted(set(str(x) for x in d['重试目标']))
        print(f"首次清除失败需重试的频道: {retry} ({len(retry)} 个)")
    if d.get('精修目标'):
        ref = sorted(set(str(x) for x in d['精修目标']))
        print(f"借助精修救回的频道      : {ref}")
    print()
    print('--- 表1 填写 ---')
    print(f"  测试案例编码     : {d.get('案例编码') or '（未记录，需从模拟器测试页面抄录）'}")
    print(f"  清除干扰源个数   : {n_clear}")
    if n_clear:
        print(f"  平均定位清除时间 : {total_v / n_clear:.1f} 秒")
    pr = d.get('程序运行时间')
    print(f"  程序运行时间     : {pr:.1f} 秒 ({pr/60:.2f} 分钟)" if pr is not None
          else "  程序运行时间     : （本日志未记录；新版本程序会在 /exit 后打印）")
    if d.get('表1块'):
        print('  [程序自报的表1 块] ' + '  '.join(f"{k}={v}" for k, v in d['表1块'].items()))
    print()
    print('提示：清除比例的分母请用演练测试界面给出的"干扰源总数"真值，')
    print('      不要用本程序自己发现的频道数——否则漏检时比例会虚高到 100%。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
