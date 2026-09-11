%% 问题2 主程序
% 计算第二检测点候选区域并推荐最优点

clear; clc; close all;

% 添加子目录到路径
addpath('utils');
addpath('visualization');

%% 1. 加载输入数据
% 可以从文件加载或直接定义
data_file = 'test_data/case2.mat';

if exist(data_file, 'file')
    load(data_file);
else
    % 手动定义测试数据
    S1 = [0, 0];
    theta1 = 45;
    r_range = [300, 800];
    alpha_range = [60, 120];
    delta_angle = 30;
    d0 = 600;
end

fprintf('=== 问题2：第二检测点选择策略 ===\n');
fprintf('第一检测点：(%.2f, %.2f)\n', S1(1), S1(2));
fprintf('第一示向度：%.2f°\n', theta1);
fprintf('距离范围：[%.0f, %.0f] 米\n', r_range(1), r_range(2));
fprintf('交会角范围：[%.0f°, %.0f°]\n', alpha_range(1), alpha_range(2));

%% 2. 计算候选区域
fprintf('\n--- 计算候选区域 ---\n');
tic;
[candidate_points, boundary_points] = compute_candidate_region(S1, theta1, r_range, alpha_range, delta_angle, d0);
time_compute = toc;

fprintf('候选点数量：%d\n', size(candidate_points, 1));
fprintf('边界点数量：%d\n', size(boundary_points, 1));
fprintf('计算耗时：%.3f 秒\n', time_compute);

%% 3. 推荐最优第二检测点
fprintf('\n--- 推荐最优点 ---\n');

% 左侧推荐点（逆时针90°）
S2_left = recommend_optimal_point(S1, theta1, 600, 'left', d0);
[alpha_left, theta2_left] = compute_intersection_angle(S1, S2_left, theta1, d0);

fprintf('左侧推荐点：(%.2f, %.2f)\n', S2_left(1), S2_left(2));
fprintf('  距离：%.2f 米\n', norm(S2_left - S1));
fprintf('  交会角：%.2f°\n', alpha_left);
fprintf('  第二示向度：%.2f°\n', theta2_left);

% 右侧推荐点（顺时针90°）
S2_right = recommend_optimal_point(S1, theta1, 600, 'right', d0);
[alpha_right, theta2_right] = compute_intersection_angle(S1, S2_right, theta1, d0);

fprintf('右侧推荐点：(%.2f, %.2f)\n', S2_right(1), S2_right(2));
fprintf('  距离：%.2f 米\n', norm(S2_right - S1));
fprintf('  交会角：%.2f°\n', alpha_right);
fprintf('  第二示向度：%.2f°\n', theta2_right);

% 选择左侧作为默认推荐
S2_optimal = S2_left;

%% 4. 可视化候选区域
fprintf('\n--- 生成可视化 ---\n');

% 确保results目录存在
if ~exist('results', 'dir')
    mkdir('results');
end

output_file_region = 'results/problem2_case2_region.png';
plot_candidate_region(S1, theta1, candidate_points, boundary_points, S2_optimal, r_range, d0, output_file_region);

%% 5. 绘制交会角热力图（可选）
output_file_heatmap = 'results/problem2_case2_heatmap.png';
plot_angle_heatmap(S1, theta1, d0, 1000, output_file_heatmap);

%% 6. 保存结果
fprintf('\n--- 保存结果 ---\n');

results = struct();
results.S1 = S1;
results.theta1 = theta1;
results.candidate_points = candidate_points;
results.boundary_points = boundary_points;
results.S2_left = S2_left;
results.S2_right = S2_right;
results.S2_optimal = S2_optimal;
results.alpha_left = alpha_left;
results.alpha_right = alpha_right;

output_file_mat = 'results/problem2_case2_results.mat';
save(output_file_mat, 'results');
fprintf('结果已保存：%s\n', output_file_mat);

fprintf('\n=== 问题2 完成 ===\n');
