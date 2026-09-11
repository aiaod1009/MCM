function plot_candidate_region(S1, theta1, candidate_points, boundary_points, S2_optimal, r_range, d0, filename)
% PLOT_CANDIDATE_REGION 绘制候选区域、第一检测点、估计干扰源、推荐最优点
%
% 输入:
%   S1               - 第一检测点坐标 [x1, y1] (米)
%   theta1           - 第一示向度 (度)
%   candidate_points - 候选区域内的点集 (N×2矩阵)
%   boundary_points  - 候选区域边界点 (M×2矩阵)
%   S2_optimal       - 推荐的最优第二检测点 [x2, y2] (米)
%   r_range          - 距离范围 [r_min, r_max] (米)
%   d0               - 估计的干扰源距离 (米)
%   filename         - 输出文件名
%
% 示例:
%   plot_candidate_region(S1, theta1, candidate_points, boundary_points, S2_optimal, [300, 800], 800, 'results/problem2_case1_region.png');

    figure('Position', [100, 100, 900, 900]);
    hold on;
    axis equal;
    grid on;

    % 绘制距离约束圆环
    theta_circle = linspace(0, 2*pi, 100);

    % 内圆（300米）
    r_inner = r_range(1);
    circle_inner_x = S1(1) + r_inner * cos(theta_circle);
    circle_inner_y = S1(2) + r_inner * sin(theta_circle);
    plot(circle_inner_x, circle_inner_y, 'k--', 'LineWidth', 1);

    % 外圆（800米）
    r_outer = r_range(2);
    circle_outer_x = S1(1) + r_outer * cos(theta_circle);
    circle_outer_y = S1(2) + r_outer * sin(theta_circle);
    plot(circle_outer_x, circle_outer_y, 'k--', 'LineWidth', 1);

    % 绘制第一示向度射线
    ray_length = 1000;
    ray_end = S1 + ray_length * [cosd(theta1), sind(theta1)];
    arrow_x = [S1(1), ray_end(1)];
    arrow_y = [S1(2), ray_end(2)];
    plot(arrow_x, arrow_y, 'k-', 'LineWidth', 2);

    % 绘制估计的干扰源位置
    G_est = S1 + d0 * [cosd(theta1), sind(theta1)];
    plot(G_est(1), G_est(2), 'bx', 'MarkerSize', 15, 'LineWidth', 3);

    % 绘制候选区域（散点）
    if ~isempty(candidate_points)
        scatter(candidate_points(:,1), candidate_points(:,2), 10, 'g', 'filled', 'MarkerFaceAlpha', 0.3);
    end

    % 绘制候选区域边界（填充）
    if ~isempty(boundary_points) && size(boundary_points, 1) >= 3
        fill(boundary_points(:,1), boundary_points(:,2), 'g', 'FaceAlpha', 0.2, 'EdgeColor', 'g', 'LineWidth', 2);
    end

    % 绘制第一检测点
    plot(S1(1), S1(2), 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 12);

    % 绘制推荐的最优点
    if ~isempty(S2_optimal)
        plot(S2_optimal(1), S2_optimal(2), 'p', 'MarkerFaceColor', 'yellow', 'MarkerEdgeColor', 'k', 'MarkerSize', 18);

        % 绘制从S2_optimal到G_est的射线（展示交会角）
        arrow_x2 = [S2_optimal(1), G_est(1)];
        arrow_y2 = [S2_optimal(2), G_est(2)];
        plot(arrow_x2, arrow_y2, 'm--', 'LineWidth', 1.5);
    end

    % 添加标注
    text(S1(1)+50, S1(2)+50, 'S_1（第一检测点）', 'FontSize', 12);
    text(G_est(1)+50, G_est(2)+50, 'G_{est}（估计干扰源）', 'FontSize', 12, 'Color', 'blue');
    if ~isempty(S2_optimal)
        text(S2_optimal(1)+50, S2_optimal(2)+50, 'S_2^*（推荐点）', 'FontSize', 12, 'Color', 'magenta');
    end

    % 设置坐标轴
    xlim([S1(1)-1000, S1(1)+1000]);
    ylim([S1(2)-1000, S1(2)+1000]);
    xlabel('X（米）');
    ylabel('Y（米）');
    title(sprintf('问题2：第二检测点候选区域（\\theta_1 = %.0f°）', theta1));

    % 图例
    legend('距离约束（内圆300米）', '距离约束（外圆800米）', '第一示向度', ...
           '估计干扰源', '候选区域点', '候选区域边界', '第一检测点', '推荐最优点', ...
           'Location', 'best');

    % 保存图片
    saveas(gcf, filename);
    fprintf('图片已保存：%s\n', filename);
    hold off;
end
