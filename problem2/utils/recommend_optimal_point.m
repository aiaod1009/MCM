function S2_optimal = recommend_optimal_point(S1, theta1, r_optimal, direction, d0)
% RECOMMEND_OPTIMAL_POINT 推荐最优第二检测点，确保交会角接近90°
%
% 输入:
%   S1         - 第一检测点坐标 [x1, y1]
%   theta1     - 第一示向度 (度)
%   r_optimal  - 推荐的S2距S1的距离 (米)，默认600
%   direction  - 方向选择：'left'或'right'，默认'left'
%   d0         - 估计的干扰源距离 (米)，默认等于r_optimal
%
% 输出:
%   S2_optimal - 推荐的最优第二检测点 [x2, y2]

    % 默认参数
    if nargin < 3 || isempty(r_optimal)
        r_optimal = 600;
    end
    if nargin < 4 || isempty(direction)
        direction = 'left';
    end
    if nargin < 5 || isempty(d0)
        d0 = r_optimal;  % 默认d0 = r_optimal
    end

    % 计算估计的干扰源位置
    G_est = S1 + d0 * [cosd(theta1), sind(theta1)];

    % 目标：使从S2指向G_est的方向为theta1±90°
    if strcmp(direction, 'left')
        theta2_target = theta1 + 90;  % 左侧（逆时针90°）
    else
        theta2_target = theta1 - 90;  % 右侧（顺时针90°）
    end

    % 从G_est出发，沿着theta2_target的反方向，距离为r_optimal的点
    % 即：S2 = G_est - r_optimal * (cos theta2_target, sin theta2_target)
    % 但这样S2距S1的距离不一定是r_optimal

    % 更严格的方法：在距S1为r_optimal的圆上搜索，使theta2最接近theta2_target

    % 采样方法：在S1周围半径r_optimal的圆上采样
    angles = 0:1:360;  % 每度采样
    min_error = inf;
    best_S2 = [];

    for angle = angles
        S2_candidate = S1 + r_optimal * [cosd(angle), sind(angle)];

        % 计算从S2到G_est的方向
        theta2 = atan2d(G_est(2) - S2_candidate(2), G_est(1) - S2_candidate(1));

        % 计算角度差
        delta = abs(theta2 - theta2_target);
        delta = min(delta, 360 - delta);

        if delta < min_error
            min_error = delta;
            best_S2 = S2_candidate;
        end
    end

    S2_optimal = best_S2;
end
