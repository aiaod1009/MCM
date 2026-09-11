function [alpha, theta2] = compute_intersection_angle(S1, S2, theta1, d0)
% COMPUTE_INTERSECTION_ANGLE 计算两个检测点对于估计干扰源位置的交会角
%
% 输入:
%   S1      - 第一检测点坐标 [x1, y1] (米)
%   S2      - 第二检测点坐标 [x2, y2] (米)
%   theta1  - 第一示向度 (度)
%   d0      - 估计的干扰源距离 (米)
%
% 输出:
%   alpha   - 交会角 (度)
%   theta2  - 第二示向度 (度)
%
% 示例:
%   S1 = [0, 0];
%   S2 = [-424, 424];
%   theta1 = 45;
%   d0 = 800;
%   [alpha, theta2] = compute_intersection_angle(S1, S2, theta1, d0);

    % 估计干扰源位置
    G_est = S1 + d0 * [cosd(theta1), sind(theta1)];

    % 计算从S2到G_est的方向（第二示向度）
    theta2 = atan2d(G_est(2) - S2(2), G_est(1) - S2(1));

    % 计算交会角
    alpha = abs(theta2 - theta1);
    alpha = min(alpha, 360 - alpha);  % 调整到[0, 180]
end
