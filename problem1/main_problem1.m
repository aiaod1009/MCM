%% 问题1 主程序
% 计算交会定位区域直径并验证覆盖性
%
% 功能：
%   1. 加载检测点数据和示向度信息
%   2. 构造每个检测点的左右边界射线
%   3. 计算所有射线对的交点
%   4. 筛选在所有扇形内的有效顶点
%   5. 计算有效顶点的凸包（定位区域）
%   6. 使用旋转卡壳算法求凸包直径
%   7. 验证覆盖圆是否能覆盖定位区域
%   8. 可视化结果并保存

clear; clc; close all;

% 添加必要的路径
addpath('utils');
addpath('visualization');

%% 1. 加载输入数据
% 可以修改这里选择不同的测试用例
% test_data/sample_case1.mat - 简单三角形配置
% test_data/sample_case2.mat - 复杂五边形配置
% test_data/sample_case3_minimal.mat - 最简双点配置

data_file = 'test_data/sample_case1.mat';

if ~exist(data_file, 'file')
    error('数据文件不存在: %s\n请先运行 visualization/generate_test_data.m 生成测试数据', data_file);
end

input_data = load(data_file);
detectors = input_data.detectors;
azimuths = input_data.azimuths;
error = input_data.error;
n = size(detectors, 1);

fprintf('=== 问题1：定位区域直径计算 ===\n');
fprintf('数据文件: %s\n', data_file);
fprintf('检测点数量: %d\n', n);
fprintf('误差范围: ±%.1f度\n\n', error);

%% 2. 构造边界射线
fprintf('【步骤1】构造边界射线...\n');

rays = [];
ray_count = 0;

for i = 1:n
    % 左边界射线
    ray_count = ray_count + 1;
    rays(ray_count).origin = detectors(i, :);
    rays(ray_count).theta = mod(azimuths(i) - error, 360);
    rays(ray_count).direction = [cosd(rays(ray_count).theta), ...
                                  sind(rays(ray_count).theta)];
    rays(ray_count).type = 'left';
    rays(ray_count).detector_id = i;

    % 右边界射线
    ray_count = ray_count + 1;
    rays(ray_count).origin = detectors(i, :);
    rays(ray_count).theta = mod(azimuths(i) + error, 360);
    rays(ray_count).direction = [cosd(rays(ray_count).theta), ...
                                  sind(rays(ray_count).theta)];
    rays(ray_count).type = 'right';
    rays(ray_count).detector_id = i;
end

fprintf('  边界射线数量: %d\n', ray_count);

%% 3. 计算所有射线交点
fprintf('\n【步骤2】计算射线交点...\n');

candidates = [];
intersection_count = 0;

for i = 1:(ray_count-1)
    for j = (i+1):ray_count
        [P, is_valid] = ray_intersection(rays(i).origin, rays(i).direction, ...
                                          rays(j).origin, rays(j).direction);
        if is_valid
            candidates = [candidates; P];
            intersection_count = intersection_count + 1;
        end
    end
end

fprintf('  候选交点数量: %d\n', size(candidates, 1));

%% 4. 筛选有效顶点
fprintf('\n【步骤3】筛选有效顶点（在所有扇形内的点）...\n');

valid_vertices = [];
for k = 1:size(candidates, 1)
    if point_in_sectors(candidates(k,:), detectors, azimuths, error)
        valid_vertices = [valid_vertices; candidates(k,:)];
    end
end

fprintf('  有效顶点数量: %d\n', size(valid_vertices, 1));

% 检查是否有有效顶点
if isempty(valid_vertices)
    error('未找到有效顶点！请检查检测点配置和示向度设置。');
end

%% 5. 计算凸包
fprintf('\n【步骤4】计算凸包（定位区域）...\n');

hull = compute_convex_hull(valid_vertices);
fprintf('  凸包顶点数量: %d\n', size(hull, 1));

% 显示凸包顶点坐标
fprintf('  凸包顶点坐标:\n');
for k = 1:size(hull, 1)
    fprintf('    顶点%d: (%.2f, %.2f)\n', k, hull(k,1), hull(k,2));
end

%% 6. 旋转卡壳求直径
fprintf('\n【步骤5】使用旋转卡壳算法计算直径...\n');

[D, V_p, V_q] = rotating_calipers(hull);

fprintf('\n=== 计算结果 ===\n');
fprintf('定位区域直径: %.4f 米\n', D);
fprintf('直径端点1: (%.2f, %.2f)\n', V_p(1), V_p(2));
fprintf('直径端点2: (%.2f, %.2f)\n', V_q(1), V_q(2));

%% 7. 验证覆盖性
fprintf('\n【步骤6】验证覆盖圆是否能覆盖定位区域...\n');

circle_center = (V_p + V_q) / 2;
circle_radius = D / 2;

% 检查所有凸包顶点是否在圆内
max_dist = 0;
worst_vertex_id = 1;  % 默认为第一个顶点

if size(hull, 1) > 0
    for k = 1:size(hull, 1)
        dist = norm(hull(k,:) - circle_center);
        if dist > max_dist
            max_dist = dist;
            worst_vertex_id = k;
        end
    end
end

fprintf('\n=== 覆盖性验证 ===\n');
fprintf('圆心坐标: (%.2f, %.2f)\n', circle_center(1), circle_center(2));
fprintf('圆半径: %.4f 米\n', circle_radius);
fprintf('凸包顶点到圆心的最大距离: %.4f 米\n', max_dist);

if size(hull, 1) > 0
    fprintf('最远顶点: 顶点%d (%.2f, %.2f)\n', ...
            worst_vertex_id, hull(worst_vertex_id,1), hull(worst_vertex_id,2));
end

% 判断覆盖性（使用小容差考虑数值误差）
tolerance = 1e-6;
if max_dist <= circle_radius + tolerance
    fprintf('\n结论: 以直径为直径的圆 能够完全覆盖定位区域 ✓\n');
    can_cover = true;
else
    fprintf('\n结论: 以直径为直径的圆 不能完全覆盖定位区域 ✗\n');
    fprintf('超出距离: %.6f 米\n', max_dist - circle_radius);
    can_cover = false;
end

%% 8. 可视化
fprintf('\n【步骤7】生成可视化图形...\n');

% 根据输入文件名生成输出文件名
[~, case_name, ~] = fileparts(data_file);
output_filename = sprintf('results/problem1_%s.png', case_name);

plot_localization_region(detectors, azimuths, error, hull, D, V_p, V_q, output_filename);

%% 9. 保存结果
fprintf('\n【步骤8】保存计算结果...\n');

results = struct();
results.data_file = data_file;
results.n_detectors = n;
results.detectors = detectors;
results.azimuths = azimuths;
results.error = error;
results.n_valid_vertices = size(valid_vertices, 1);
results.hull = hull;
results.diameter = D;
results.endpoint1 = V_p;
results.endpoint2 = V_q;
results.circle_center = circle_center;
results.circle_radius = circle_radius;
results.max_distance = max_dist;
results.can_cover = can_cover;

% 保存结果到 .mat 文件
result_mat_file = sprintf('results/problem1_%s_results.mat', case_name);
save(result_mat_file, 'results');
fprintf('结果已保存到: %s\n', result_mat_file);

% 保存结果到文本文件
result_txt_file = sprintf('results/problem1_%s_results.txt', case_name);
fid = fopen(result_txt_file, 'w');
fprintf(fid, '=== 问题1：定位区域直径计算结果 ===\n\n');
fprintf(fid, '数据文件: %s\n', data_file);
fprintf(fid, '检测点数量: %d\n', n);
fprintf(fid, '误差范围: ±%.1f度\n\n', error);

fprintf(fid, '--- 检测点信息 ---\n');
for i = 1:n
    fprintf(fid, '检测点%d: (%.2f, %.2f), 示向度 %.1f°\n', ...
            i, detectors(i,1), detectors(i,2), azimuths(i));
end

fprintf(fid, '\n--- 计算结果 ---\n');
fprintf(fid, '有效顶点数量: %d\n', size(valid_vertices, 1));
fprintf(fid, '凸包顶点数量: %d\n', size(hull, 1));
fprintf(fid, '定位区域直径: %.4f 米\n', D);
fprintf(fid, '直径端点1: (%.2f, %.2f)\n', V_p(1), V_p(2));
fprintf(fid, '直径端点2: (%.2f, %.2f)\n', V_q(1), V_q(2));

fprintf(fid, '\n--- 覆盖性验证 ---\n');
fprintf(fid, '圆心坐标: (%.2f, %.2f)\n', circle_center(1), circle_center(2));
fprintf(fid, '圆半径: %.4f 米\n', circle_radius);
fprintf(fid, '凸包顶点到圆心的最大距离: %.4f 米\n', max_dist);

if can_cover
    fprintf(fid, '结论: 能够覆盖 ✓\n');
else
    fprintf(fid, '结论: 不能完全覆盖 ✗\n');
    fprintf(fid, '超出距离: %.6f 米\n', max_dist - circle_radius);
end

fclose(fid);
fprintf('结果已保存到: %s\n', result_txt_file);

fprintf('\n=== 程序执行完毕 ===\n');
