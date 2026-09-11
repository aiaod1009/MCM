function plot_localization_region(detectors, azimuths, error, hull, D, V_p, V_q, filename)
% PLOT_LOCALIZATION_REGION 绘制定位区域、边界射线、凸包、直径
%
% 输入:
%   detectors - 检测点坐标矩阵 n×2
%   azimuths - 示向度向量 n×1（度）
%   error - 误差范围（度）
%   hull - 凸包顶点矩阵 m×2
%   D - 直径长度
%   V_p - 直径端点1坐标 [x, y]
%   V_q - 直径端点2坐标 [x, y]
%   filename - 输出图片文件名
%
% 输出:
%   保存图片到指定文件

    % 创建图形窗口
    figure('Position', [100, 100, 800, 800]);
    hold on;
    axis equal;
    grid on;

    n = size(detectors, 1);

    % 计算射线显示长度（根据场景自适应）
    if D > 0
        ray_length = max(1000, D * 2);
    else
        ray_length = 1000;
    end

    %% 1. 绘制边界射线
    for i = 1:n
        origin = detectors(i, :);

        % 左边界射线（红色虚线）
        theta_L = azimuths(i) - error;
        dir_L = [cosd(theta_L), sind(theta_L)];
        endpoint_L = origin + ray_length * dir_L;
        plot([origin(1), endpoint_L(1)], [origin(2), endpoint_L(2)], ...
             'r--', 'LineWidth', 0.5);

        % 右边界射线（蓝色虚线）
        theta_R = azimuths(i) + error;
        dir_R = [cosd(theta_R), sind(theta_R)];
        endpoint_R = origin + ray_length * dir_R;
        plot([origin(1), endpoint_R(1)], [origin(2), endpoint_R(2)], ...
             'b--', 'LineWidth', 0.5);

        % 中心示向度射线（黑色实线）
        dir_C = [cosd(azimuths(i)), sind(azimuths(i))];
        endpoint_C = origin + ray_length * dir_C;
        plot([origin(1), endpoint_C(1)], [origin(2), endpoint_C(2)], ...
             'k-', 'LineWidth', 1.5);
    end

    %% 2. 绘制检测点（黄色圆点）
    plot(detectors(:,1), detectors(:,2), 'ko', ...
         'MarkerFaceColor', 'yellow', 'MarkerSize', 10);

    %% 3. 绘制凸包（定位区域）
    if ~isempty(hull) && size(hull, 1) > 0
        % 闭合多边形
        hull_closed = [hull; hull(1,:)];

        % 填充定位区域（青色半透明）
        fill(hull_closed(:,1), hull_closed(:,2), 'cyan', ...
             'FaceAlpha', 0.3, 'EdgeColor', 'blue', 'LineWidth', 2);
    end

    %% 4. 绘制直径
    if D > 0
        % 直径线段（洋红色粗线）
        plot([V_p(1), V_q(1)], [V_p(2), V_q(2)], ...
             'm-', 'LineWidth', 3);

        % 直径端点（洋红色圆点）
        plot(V_p(1), V_p(2), 'mo', ...
             'MarkerFaceColor', 'magenta', 'MarkerSize', 8);
        plot(V_q(1), V_q(2), 'mo', ...
             'MarkerFaceColor', 'magenta', 'MarkerSize', 8);

        %% 5. 绘制以直径为直径的覆盖圆
        circle_center = (V_p + V_q) / 2;
        circle_radius = D / 2;
        theta_circle = linspace(0, 2*pi, 100);
        circle_x = circle_center(1) + circle_radius * cos(theta_circle);
        circle_y = circle_center(2) + circle_radius * sin(theta_circle);
        plot(circle_x, circle_y, 'g-', 'LineWidth', 2);
    end

    %% 6. 添加标注和图例
    title(sprintf('定位区域与直径 (D = %.2f 米)', D), 'FontSize', 14);
    xlabel('X (米)', 'FontSize', 12);
    ylabel('Y (米)', 'FontSize', 12);

    % 图例
    legend('左边界射线', '右边界射线', '示向度中心', '检测点', ...
           '定位区域', '直径', '', '', '覆盖圆', ...
           'Location', 'best');

    %% 7. 自动调整坐标轴范围
    if ~isempty(hull) && size(hull, 1) > 0
        x_min = min(hull(:,1));
        x_max = max(hull(:,1));
        y_min = min(hull(:,2));
        y_max = max(hull(:,2));

        % 添加边距
        margin = max(D * 0.2, 20);
        xlim([x_min - margin, x_max + margin]);
        ylim([y_min - margin, y_max + margin]);
    end

    %% 8. 保存图片
    saveas(gcf, filename);
    fprintf('图片已保存: %s\n', filename);

    hold off;
end
