function plot_angle_heatmap(S1, theta1, d0, r_max, filename)
% PLOT_ANGLE_HEATMAP 绘制极坐标下的交会角热力图
%
% 输入:
%   S1       - 第一检测点坐标 [x1, y1] (米)
%   theta1   - 第一示向度 (度)
%   d0       - 估计的干扰源距离 (米)
%   r_max    - 最大绘制半径 (米)
%   filename - 输出文件名
%
% 示例:
%   plot_angle_heatmap([0, 0], 45, 800, 1000, 'results/problem2_case1_heatmap.png');

    % 添加utils路径以调用compute_intersection_angle
    addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'utils'));

    % 生成极坐标网格
    r_samples = 0:20:r_max;
    phi_samples = 0:2:360;

    [R_grid, PHI_grid] = meshgrid(r_samples, phi_samples);

    % 估计干扰源位置
    G_est = S1 + d0 * [cosd(theta1), sind(theta1)];

    % 计算每个点的交会角
    ALPHA_grid = zeros(size(R_grid));

    for i = 1:size(R_grid, 1)
        for j = 1:size(R_grid, 2)
            r = R_grid(i, j);
            phi = PHI_grid(i, j);

            if r == 0
                ALPHA_grid(i, j) = NaN;
                continue;
            end

            % 第二检测点坐标
            S2 = S1 + r * [cosd(phi), sind(phi)];

            % 计算交会角
            [alpha, ~] = compute_intersection_angle(S1, S2, theta1, d0);
            ALPHA_grid(i, j) = alpha;
        end
    end

    % 绘制热力图
    figure('Position', [100, 100, 800, 800]);

    % 转换为笛卡尔坐标
    X_grid = R_grid .* cosd(PHI_grid);
    Y_grid = R_grid .* sind(PHI_grid);

    pcolor(X_grid, Y_grid, ALPHA_grid);
    shading interp;
    axis equal;
    colorbar;
    colormap(jet);
    caxis([0, 180]);

    xlabel('X（米）');
    ylabel('Y（米）');
    title(sprintf('交会角热力图（\\theta_1 = %.0f°）', theta1));

    % 添加颜色条标签
    c = colorbar;
    c.Label.String = '交会角（度）';

    % 保存图片
    saveas(gcf, filename);
    fprintf('热力图已保存：%s\n', filename);
end
