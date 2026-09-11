function plot_fixed_search_circle(S1, theta1, d0, output_file)
% PLOT_FIXED_SEARCH_CIRCLE 绘制8.4节固定搜索圆示意图
%
% 输入参数：
%   S1          - 第一检测点坐标 [x, y]
%   theta1      - 第一示向度（度）
%   d0          - 估计干扰源距离（米）
%   output_file - 输出文件路径
%
% 功能：
%   绘制固定搜索圆（r=600m），显示：
%   1. 第一检测点 S1
%   2. 搜索圆（r=600m）
%   3. 圆周上360个采样点（Δφ=1°）
%   4. 估计干扰源位置 G_est
%   5. 第一示向线
%   6. 最终推荐点 S2*（交会角≈90°）
%   7. 交会角标注

% 固定参数
r_fixed = 600;  % 固定搜索半径（米）
delta_phi = 1;  % 角度采样间隔（度）

% 计算估计干扰源位置
G_est = S1 + d0 * [cosd(theta1), sind(theta1)];

% 生成搜索圆上的360个采样点
angles = 0:delta_phi:360-delta_phi;  % 0°到359°，共360个点
n_samples = length(angles);
sample_points = zeros(n_samples, 2);

for i = 1:n_samples
    phi = angles(i);
    sample_points(i, :) = S1 + r_fixed * [cosd(phi), sind(phi)];
end

% 计算最优推荐点（垂直于第一示向线）
% 选择左侧（逆时针90°）
phi_optimal = theta1 + 90;
S2_optimal = S1 + r_fixed * [cosd(phi_optimal), sind(phi_optimal)];

% 计算交会角
vec1 = G_est - S1;
vec2 = G_est - S2_optimal;
cos_alpha = dot(vec1, vec2) / (norm(vec1) * norm(vec2));
alpha_optimal = acosd(cos_alpha);

% 创建图形
figure('Position', [100, 100, 1000, 900]);
hold on; grid on; axis equal;

% 1. 绘制搜索圆
theta_circle = linspace(0, 2*pi, 500);
x_circle = S1(1) + r_fixed * cos(theta_circle);
y_circle = S1(2) + r_fixed * sin(theta_circle);
plot(x_circle, y_circle, 'k-', 'LineWidth', 2, 'DisplayName', '搜索圆 (r=600m)');

% 2. 绘制圆周上的360个采样点
plot(sample_points(:,1), sample_points(:,2), 'b.', 'MarkerSize', 4, ...
    'DisplayName', sprintf('采样点 (N=%d, Δφ=%d°)', n_samples, delta_phi));

% 3. 绘制第一检测点
plot(S1(1), S1(2), 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r', ...
    'LineWidth', 2, 'DisplayName', '第一检测点 S_1');

% 4. 绘制第一示向线
line_length = d0 * 1.2;
x_line = [S1(1), S1(1) + line_length * cosd(theta1)];
y_line = [S1(2), S1(2) + line_length * sind(theta1)];
plot(x_line, y_line, 'k--', 'LineWidth', 1.5, 'DisplayName', '第一示向线');

% 5. 绘制估计干扰源位置
plot(G_est(1), G_est(2), 'bx', 'MarkerSize', 15, 'LineWidth', 3, ...
    'DisplayName', 'G_{est} (估计干扰源)');

% 6. 绘制最终推荐点
plot(S2_optimal(1), S2_optimal(2), 'mp', 'MarkerSize', 18, ...
    'MarkerFaceColor', 'm', 'LineWidth', 2, 'DisplayName', '推荐点 S_2^*');

% 7. 绘制从S2到G_est的连线（用于显示交会角）
plot([S2_optimal(1), G_est(1)], [S2_optimal(2), G_est(2)], ...
    'm--', 'LineWidth', 1.5, 'DisplayName', '第二示向线');

% 8. 标注交会角
% 在G_est附近标注交会角
text(G_est(1) + 50, G_est(2) + 50, ...
    sprintf('α ≈ %.1f°', alpha_optimal), ...
    'FontSize', 14, 'FontWeight', 'bold', 'Color', 'red', ...
    'BackgroundColor', 'white', 'EdgeColor', 'red');

% 9. 添加距离标注
mid_point = (S1 + S2_optimal) / 2;
text(mid_point(1), mid_point(2) - 50, ...
    sprintf('||S_2-S_1|| = %d m', r_fixed), ...
    'FontSize', 12, 'FontWeight', 'bold', 'BackgroundColor', 'white');

% 10. 添加点标签
text(S1(1) - 80, S1(2) - 80, 'S_1', 'FontSize', 14, 'FontWeight', 'bold');
text(S2_optimal(1) - 80, S2_optimal(2) + 80, 'S_2^*', 'FontSize', 14, 'FontWeight', 'bold');
text(G_est(1) + 80, G_est(2), 'G_{est}', 'FontSize', 14, 'FontWeight', 'bold');

% 设置坐标轴
xlabel('东向距离 (米)', 'FontSize', 12);
ylabel('北向距离 (米)', 'FontSize', 12);
title(sprintf('8.4节 固定搜索圆策略 (r=%dm, Δφ=%d°, N=%d)', ...
    r_fixed, delta_phi, n_samples), 'FontSize', 14, 'FontWeight', 'bold');

% 图例
legend('Location', 'best', 'FontSize', 10);

% 保存图片
if nargin >= 4 && ~isempty(output_file)
    saveas(gcf, output_file);
    fprintf('固定搜索圆示意图已保存：%s\n', output_file);
end

hold off;

end
