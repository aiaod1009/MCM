function plot_localization_region(detectors, azimuths, error, hull, D, V_p, V_q, filename)
% PLOT_LOCALIZATION_REGION 绘制定位区域、边界射线、凸包、直径与覆盖圆
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
%
% 【改写 2026-09-12】改为双面板布局：左图给出检测点、示向度边界射线与定位
%   区域的全局相对位置，右图放大了定位区域本身、区域直径与覆盖圆。
%   原因是交会定位区域的尺度通常比检测点间距小 1~2 个数量级（实测案例中
%   最小相差约 29 倍），单面板视图下定位区域会被压缩成难以辨认的一点。

    figure('Position', [80, 80, 1100, 540]);

    if D > 0
        ray_length = max(1000, D * 2);
    else
        ray_length = 1000;
    end

    has_hull = ~isempty(hull) && size(hull, 1) > 0;

    %% ---------- 左面板：全局视图 ----------
    ax1 = subplot(1, 2, 1);
    hold(ax1, 'on'); axis(ax1, 'equal'); grid(ax1, 'on');
    [h_rayL, h_rayR, h_rayC, h_det, h_hull, h_diam, h_circle] = ...
        draw_scene(ax1, detectors, azimuths, error, hull, D, V_p, V_q, ray_length);

    title(ax1, '全局视图', 'FontSize', 14);
    xlabel(ax1, 'X (米)', 'FontSize', 12);
    ylabel(ax1, 'Y (米)', 'FontSize', 12);
    set(ax1, 'FontSize', 11);

    % 图例：逐项绑定句柄，避免依赖绘制顺序造成错位
    h_list = []; lab_list = {};
    if ~isempty(h_rayL), h_list(end+1) = h_rayL; lab_list{end+1} = '左边界射线'; end
    if ~isempty(h_rayR), h_list(end+1) = h_rayR; lab_list{end+1} = '右边界射线'; end
    if ~isempty(h_rayC), h_list(end+1) = h_rayC; lab_list{end+1} = '示向度中心'; end
    if ~isempty(h_det),  h_list(end+1) = h_det;  lab_list{end+1} = '检测点'; end
    if ~isempty(h_hull), h_list(end+1) = h_hull; lab_list{end+1} = '定位区域'; end
    if ~isempty(h_diam), h_list(end+1) = h_diam; lab_list{end+1} = '区域直径'; end
    if ~isempty(h_circle)
        h_list(end+1) = h_circle; lab_list{end+1} = '覆盖圆(以D为直径)';
    end
    legend(ax1, h_list, lab_list, 'Location', 'southoutside', ...
           'Orientation', 'horizontal', 'NumColumns', 4, 'FontSize', 9);

    if has_hull
        all_pts = [detectors; hull];
        span = max(max(all_pts) - min(all_pts));
        pad = max(span * 0.10, eps);
        xlim(ax1, [min(all_pts(:,1)) - pad, max(all_pts(:,1)) + pad]);
        ylim(ax1, [min(all_pts(:,2)) - pad, max(all_pts(:,2)) + pad]);
    end

    %% ---------- 右面板：定位区域放大 ----------
    ax2 = subplot(1, 2, 2);
    hold(ax2, 'on'); axis(ax2, 'equal'); grid(ax2, 'on');
    draw_scene(ax2, detectors, azimuths, error, hull, D, V_p, V_q, ray_length);

    title(ax2, sprintf('定位区域放大 (D = %.4f 米)', D), 'FontSize', 14);
    xlabel(ax2, 'X (米)', 'FontSize', 12);
    ylabel(ax2, 'Y (米)', 'FontSize', 12);
    set(ax2, 'FontSize', 11);

    if has_hull
        pad = max(D * 0.45, 0.5);
        xlim(ax2, [min(hull(:,1)) - pad, max(hull(:,1)) + pad]);
        ylim(ax2, [min(hull(:,2)) - pad, max(hull(:,2)) + pad]);
    end

    % 放大视图下坐标范围很小，用两位小数刻度避免标签重复
    xtickformat(ax2, '%.2f');
    ytickformat(ax2, '%.2f');

    % 以高分辨率、紧边界导出，避免四周留白并保证缩放后文字清晰
    try
        exportgraphics(gcf, filename, 'Resolution', 200, 'BackgroundColor', 'white');
    catch
        saveas(gcf, filename);
    end
    fprintf('图片已保存: %s\n', filename);
end


function [h_rayL, h_rayR, h_rayC, h_det, h_hull, h_diam, h_circle] = ...
        draw_scene(ax, detectors, azimuths, error, hull, D, V_p, V_q, ray_length)
% DRAW_SCENE 在指定坐标轴上绘制全部几何元素，并返回句柄供图例绑定

    n = size(detectors, 1);

    h_rayL = []; h_rayR = []; h_rayC = [];
    for i = 1:n
        origin = detectors(i, :);

        % 左、右边界射线
        for k = 1:2
            th = azimuths(i) + (2*k - 3) * error;   % k=1: -error, k=2: +error
            endpoint = origin + ray_length * [cosd(th), sind(th)];
            if k == 1
                h = plot(ax, [origin(1), endpoint(1)], [origin(2), endpoint(2)], ...
                         'r--', 'LineWidth', 0.5);
                if i == 1, h_rayL = h; end
            else
                h = plot(ax, [origin(1), endpoint(1)], [origin(2), endpoint(2)], ...
                         'b--', 'LineWidth', 0.5);
                if i == 1, h_rayR = h; end
            end
        end

        % 中心示向度射线
        endpoint = origin + ray_length * [cosd(azimuths(i)), sind(azimuths(i))];
        h = plot(ax, [origin(1), endpoint(1)], [origin(2), endpoint(2)], ...
                 'k-', 'LineWidth', 1.2);
        if i == 1, h_rayC = h; end
    end

    % 检测点
    h_det = plot(ax, detectors(:,1), detectors(:,2), 'ko', ...
                 'MarkerFaceColor', 'yellow', 'MarkerSize', 8);

    % 定位区域（凸包）
    h_hull = [];
    if ~isempty(hull) && size(hull, 1) > 0
        hull_closed = [hull; hull(1,:)];
        h_hull = fill(ax, hull_closed(:,1), hull_closed(:,2), 'cyan', ...
                      'FaceAlpha', 0.35, 'EdgeColor', 'blue', 'LineWidth', 1.5);
    end

    % 直径与覆盖圆
    h_diam = []; h_circle = [];
    if D > 0
        h_diam = plot(ax, [V_p(1), V_q(1)], [V_p(2), V_q(2)], 'm-', 'LineWidth', 2.5);
        plot(ax, V_p(1), V_p(2), 'mo', 'MarkerFaceColor', 'magenta', 'MarkerSize', 7);
        plot(ax, V_q(1), V_q(2), 'mo', 'MarkerFaceColor', 'magenta', 'MarkerSize', 7);

        circle_center = (V_p + V_q) / 2;
        theta_circle = linspace(0, 2*pi, 200);
        h_circle = plot(ax, circle_center(1) + D/2 * cos(theta_circle), ...
                            circle_center(2) + D/2 * sin(theta_circle), ...
                        'g-', 'LineWidth', 1.8);
    end
end
