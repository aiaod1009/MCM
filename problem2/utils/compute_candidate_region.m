function [candidate_points, boundary_points] = compute_candidate_region(S1, theta1, r_range, alpha_range, delta_angle, d0)
% COMPUTE_CANDIDATE_REGION 根据约束条件计算第二检测点的候选区域
%
% 输入:
%   S1          - 第一检测点坐标 [x1, y1] (米)
%   theta1      - 第一示向度 (度)
%   r_range     - 距离范围 [r_min, r_max] (米)
%   alpha_range - 交会角范围 [alpha_min, alpha_max] (度)
%   delta_angle - 避免平行方向的排除角度 (度)
%   d0          - 估计的干扰源距离 (米)
%
% 输出:
%   candidate_points - 候选区域内的点集 (N×2矩阵)
%   boundary_points  - 候选区域边界点 (M×2矩阵)
%
% 示例:
%   S1 = [0, 0];
%   theta1 = 45;
%   [candidate_points, boundary_points] = compute_candidate_region(S1, theta1, [300, 800], [60, 120], 30, 800);

    % 步骤1：生成采样网格
    r_min = r_range(1);
    r_max = r_range(2);
    alpha_min = alpha_range(1);
    alpha_max = alpha_range(2);

    % 极坐标采样
    r_samples = r_min:50:r_max;         % 距离采样，步长50米
    phi_samples = 0:5:360;              % 角度采样，步长5度

    % 转换为笛卡尔坐标
    [R_grid, PHI_grid] = meshgrid(r_samples, phi_samples);
    X_grid = S1(1) + R_grid .* cosd(PHI_grid);
    Y_grid = S1(2) + R_grid .* sind(PHI_grid);

    % 展平为点集
    X_flat = X_grid(:);
    Y_flat = Y_grid(:);

    % 步骤2：估计干扰源位置
    G_est = S1 + d0 * [cosd(theta1), sind(theta1)];

    % 步骤3：筛选满足约束的点
    candidate_points = [];

    for i = 1:length(X_flat)
        S2 = [X_flat(i), Y_flat(i)];

        % 约束1：距离约束（已通过采样保证，跳过）

        % 约束2：交会角约束
        % 从S2到G_est的方向
        theta2 = atan2d(G_est(2) - S2(2), G_est(1) - S2(1));

        % 计算交会角
        alpha = abs(theta2 - theta1);
        alpha = min(alpha, 360 - alpha);  % 调整到[0, 180]

        if alpha < alpha_min || alpha > alpha_max
            continue;  % 不满足交会角约束，跳过
        end

        % 约束3：避免平行方向
        % 从S1到S2的方向
        beta = atan2d(S2(2) - S1(2), S2(1) - S1(1));

        % 计算角度差
        delta_beta = abs(beta - theta1);
        delta_beta = min(delta_beta, 360 - delta_beta);

        if delta_beta < delta_angle || delta_beta > (180 - delta_angle)
            continue;  % 在排除区域内，跳过
        end

        % 通过所有约束，加入候选区域
        candidate_points = [candidate_points; S2];
    end

    % 步骤4：提取边界
    if size(candidate_points, 1) >= 3
        % 使用凸包提取边界
        K = convhull(candidate_points(:,1), candidate_points(:,2));
        boundary_points = candidate_points(K, :);
        % 去除重复的首尾点
        boundary_points = boundary_points(1:end-1, :);
    else
        boundary_points = candidate_points;
    end
end
