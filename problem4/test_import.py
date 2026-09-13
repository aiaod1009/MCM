# -*- coding: utf-8 -*-
"""
快速验证脚本：测试所有模块是否能正常导入
"""
import sys
import os

print("="*60)
print("问题4模块导入测试")
print("="*60)

# 添加路径
src_path = os.path.join(os.path.dirname(__file__), 'src')
problem3_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../问题3/MCM/problem3/src'))
sys.path.append(src_path)
sys.path.append(problem3_src_path)

test_results = []

# 测试1：导入分类器
print("\n[1] 测试导入SourceClassifier...")
try:
    from classification.source_classifier import SourceClassifier
    classifier = SourceClassifier()
    print("✅ SourceClassifier 导入成功")
    test_results.append(("SourceClassifier", True))
except Exception as e:
    print(f"❌ SourceClassifier 导入失败: {e}")
    test_results.append(("SourceClassifier", False))

# 测试2：导入楔形定位器
print("\n[2] 测试导入WedgeLocalizer...")
try:
    from classification.wedge_localization import WedgeLocalizer
    localizer = WedgeLocalizer()
    print("✅ WedgeLocalizer 导入成功")
    test_results.append(("WedgeLocalizer", True))
except Exception as e:
    print(f"❌ WedgeLocalizer 导入失败: {e}")
    test_results.append(("WedgeLocalizer", False))

# 测试3：导入增强扫描器
print("\n[3] 测试导入EnhancedScanner...")
try:
    from phase1_enhanced_scan import EnhancedScanner
    # scanner = EnhancedScanner('test_robot')  # 需要模拟器
    print("✅ EnhancedScanner 导入成功（未实例化）")
    test_results.append(("EnhancedScanner", True))
except Exception as e:
    print(f"❌ EnhancedScanner 导入失败: {e}")
    test_results.append(("EnhancedScanner", False))

# 测试4：导入分类定位器
print("\n[4] 测试导入ClassificationLocalizer...")
try:
    from phase2_classification_localization import ClassificationLocalizer
    clf_localizer = ClassificationLocalizer()
    print("✅ ClassificationLocalizer 导入成功")
    test_results.append(("ClassificationLocalizer", True))
except Exception as e:
    print(f"❌ ClassificationLocalizer 导入失败: {e}")
    test_results.append(("ClassificationLocalizer", False))

# 测试5：导入主程序
print("\n[5] 测试导入Problem4Solver...")
try:
    from main_problem4 import Problem4Solver, ClearingPhaseWrapper
    # solver = Problem4Solver('test_robot')  # 需要模拟器
    print("✅ Problem4Solver 导入成功（未实例化）")
    test_results.append(("Problem4Solver", True))
except Exception as e:
    print(f"❌ Problem4Solver 导入失败: {e}")
    test_results.append(("Problem4Solver", False))

# 测试6：测试分类器功能
print("\n[6] 测试SourceClassifier基本功能...")
try:
    classifier = SourceClassifier()

    # 模拟全向源数据（所有点都有信号）
    omnidirectional_data = [
        ((900, 0), {'type': 'direction', 'azimuth': 3.14}),
        ((0, 900), {'type': 'direction', 'azimuth': 4.71}),
        ((-900, 0), {'type': 'direction', 'azimuth': 0.0}),
        ((0, -900), {'type': 'direction', 'azimuth': 1.57}),
    ]

    source_type, conf = classifier.classify(omnidirectional_data)
    print(f"  全向源测试：{source_type} (置信度: {conf:.2f})")

    if source_type == 'omnidirectional':
        print("✅ 全向源判断正确")
        test_results.append(("Classifier_Omnidirectional", True))
    else:
        print("⚠️  全向源判断可能有误")
        test_results.append(("Classifier_Omnidirectional", False))

except Exception as e:
    print(f"❌ SourceClassifier功能测试失败: {e}")
    test_results.append(("Classifier_Omnidirectional", False))

# 测试7：测试分类器功能（定向源）
print("\n[7] 测试SourceClassifier定向源判断...")
try:
    # 模拟定向源数据（部分点有信号，部分无信号）
    directional_data = [
        ((900, 0), {'type': 'direction', 'azimuth': 3.14}),
        ((600, 600), {'type': 'direction', 'azimuth': 3.5}),
        ((-900, 0), {'type': 'no_signal'}),
        ((-600, -600), {'type': 'no_signal'}),
        ((0, -900), {'type': 'no_signal'}),
    ]

    source_type, conf = classifier.classify(directional_data)
    print(f"  定向源测试：{source_type} (置信度: {conf:.2f})")

    if source_type == 'directional':
        print("✅ 定向源判断正确")
        test_results.append(("Classifier_Directional", True))
    else:
        print("⚠️  定向源判断可能有误")
        test_results.append(("Classifier_Directional", False))

except Exception as e:
    print(f"❌ SourceClassifier定向源测试失败: {e}")
    test_results.append(("Classifier_Directional", False))

# 打印汇总
print("\n" + "="*60)
print("测试汇总")
print("="*60)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for name, result in test_results:
    status = "✅ 通过" if result else "❌ 失败"
    print(f"{name:30s} {status}")

print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

if passed == total:
    print("\n🎉 所有测试通过！代码准备就绪！")
    print("\n下一步：运行完整测试")
    print("python src/main_problem4.py --robot-id 202619020062")
else:
    print(f"\n⚠️  {total-passed}个测试失败，需要检查代码")

print("="*60)
