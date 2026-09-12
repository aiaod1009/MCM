%% 运行所有测试用例
% 依次运行所有测试数据并生成结果

clear; clc; close all;

fprintf('=== 运行所有测试用例 ===\n\n');

% 添加必要的路径
addpath('utils');
addpath('visualization');

% 测试用例列表
test_cases = {
    'test_data/sample_case1.mat', '简单三角形配置';
    'test_data/sample_case2.mat', '五检测点配置(±1°)';
    'test_data/sample_case3_minimal.mat', '双点最小配置';
    'test_data/sample_case4_equilateral.mat', '等边三检测点(圆盖不住反例)'
};

% 角度容差（度）：交会区域顶点必然落在约束边界上，需容差避免浮点误杀
% 【修正 2026-09-12】原脚本漏传该容差，会重现案例1/案例3 的错误结果。
ang_tol = 1e-9;

% 统计信息
total_cases = size(test_cases, 1);
success_count = 0;
failed_cases = {};

%% 遍历所有测试用例
for idx = 1:total_cases
    data_file = test_cases{idx, 1};
    description = test_cases{idx, 2};

    fprintf('=============================================================\n');
    fprintf('测试用例 %d/%d: %s\n', idx, total_cases, description);
    fprintf('数据文件: %s\n', data_file);
    fprintf('=============================================================\n\n');

    try
        %% 1. 加载输入数据
        if ~exist(data_file, 'file')
            error('数据文件不存在: %s', data_file);
        end

        input_data = load(data_file);
        detectors = input_data.detectors;
        azimuths = input_data.azimuths;
        error_range = input_data.error;
        n = size(detectors, 1);

        fprintf('检测点数量: %d\n', n);
        fprintf('误差范围: ±%.1f度\n', error_range);

        %% 2. 构造边界射线
        rays = [];
        ray_count = 0;

        for i = 1:n
            % 左边界射线
            ray_count = ray_count + 1;
            rays(ray_count).origin = detectors(i, :);
            rays(ray_count).theta = mod(azimuths(i) - error_range, 360);
            rays(ray_count).direction = [cosd(rays(ray_count).theta), ...
                                          sind(rays(ray_count).theta)];

            % 右边界射线
            ray_count = ray_count + 1;
            rays(ray_count).origin = detectors(i, :);
            rays(ray_count).theta = mod(azimuths(i) + error_range, 360);
            rays(ray_count).direction = [cosd(rays(ray_count).theta), ...
                                          sind(rays(ray_count).theta)];
        end

        %% 3. 计算所有射线交点
        candidates = [];
        for i = 1:(ray_count-1)
            for j = (i+1):ray_count
                [P, is_valid] = ray_intersection(rays(i).origin, rays(i).direction, ...
                                                  rays(j).origin, rays(j).direction);
                if is_valid
                    candidates = [candidates; P];
                end
            end
        end

        fprintf('候选交点数量: %d\n', size(candidates, 1));

        %% 4. 筛选有效顶点
        valid_vertices = [];
        for k = 1:size(candidates, 1)
            % 【修正 2026-09-12】传入角度容差，避免落在约束边界上的顶点被
            % atan2d 的浮点误差误杀（这是原版直径严重偏小的根因）
            if point_in_sectors(candidates(k,:), detectors, azimuths, error_range, ang_tol)
                valid_vertices = [valid_vertices; candidates(k,:)];
            end
        end

        fprintf('有效顶点数量: %d\n', size(valid_vertices, 1));

        if isempty(valid_vertices)
            warning('未找到有效顶点，跳过此测试用例');
            failed_cases{end+1} = sprintf('%s (无有效顶点)', description);
            continue;
        end

        %% 5. 计算凸包
        hull = compute_convex_hull(valid_vertices);
        fprintf('凸包顶点数量: %d\n', size(hull, 1));

        %% 6. 旋转卡壳求直径
        [D, V_p, V_q] = rotating_calipers(hull);

        fprintf('\n--- 计算结果 ---\n');
        fprintf('定位区域直径: %.4f 米\n', D);
        fprintf('直径端点1: (%.2f, %.2f)\n', V_p(1), V_p(2));
        fprintf('直径端点2: (%.2f, %.2f)\n', V_q(1), V_q(2));

        %% 7. 验证覆盖性
        circle_center = (V_p + V_q) / 2;
        circle_radius = D / 2;

        max_dist = 0;
        if size(hull, 1) > 0
            for k = 1:size(hull, 1)
                dist = norm(hull(k,:) - circle_center);
                if dist > max_dist
                    max_dist = dist;
                end
            end
        end

        fprintf('\n--- 覆盖性验证 ---\n');
        fprintf('圆半径: %.4f 米\n', circle_radius);
        fprintf('最大距离: %.4f 米\n', max_dist);

        tolerance = 1e-9 * max(1, D);
        if max_dist <= circle_radius + tolerance
            fprintf('结论: 能够覆盖 ✓\n');
            can_cover = true;
        else
            fprintf('结论: 不能完全覆盖 ✗ (超出 %.6f 米)\n', max_dist - circle_radius);
            can_cover = false;
        end

        %% 8. 可视化
        [~, case_name, ~] = fileparts(data_file);
        output_filename = sprintf('results/problem1_%s.png', case_name);
        plot_localization_region(detectors, azimuths, error_range, hull, D, V_p, V_q, output_filename);

        %% 9. 保存结果
        results = struct();
        results.data_file = data_file;
        results.diameter = D;
        results.can_cover = can_cover;

        result_mat_file = sprintf('results/problem1_%s_results.mat', case_name);
        save(result_mat_file, 'results');

        success_count = success_count + 1;
        fprintf('\n✓ 测试用例执行成功\n\n');

    catch ME
        fprintf('\n✗ 测试用例执行失败\n');
        fprintf('错误信息: %s\n\n', ME.message);
        failed_cases{end+1} = sprintf('%s (%s)', description, ME.message);
    end
end

%% 汇总统计
fprintf('=============================================================\n');
fprintf('测试汇总\n');
fprintf('=============================================================\n');
fprintf('总计: %d 个测试用例\n', total_cases);
fprintf('成功: %d 个\n', success_count);
fprintf('失败: %d 个\n', total_cases - success_count);

if ~isempty(failed_cases)
    fprintf('\n失败的测试用例:\n');
    for i = 1:length(failed_cases)
        fprintf('  %d. %s\n', i, failed_cases{i});
    end
end

fprintf('\n所有测试完成！\n');
