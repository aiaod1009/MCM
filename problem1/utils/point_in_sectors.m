function is_inside = point_in_sectors(P, detectors, azimuths, error)
% POINT_IN_SECTORS 判断点是否在所有检测点的扇形区域内
%
% 输入:
%   P - 待判断点坐标 [x, y]
%   detectors - 检测点坐标矩阵 n×2
%   azimuths - 示向度向量 n×1（度）
%   error - 误差范围（度）
%
% 输出:
%   is_inside - 布尔值，true表示点在所有扇形内，false表示至少有一个不在
%
% 算法原理:
%   对每个检测点：
%   1. 计算从检测点到P的方位角
%   2. 判断该角度是否在 [azimuth-error, azimuth+error] 范围内
%   3. 需要特别处理跨越0度的情况

    n = size(detectors, 1);
    is_inside = true;

    for i = 1:n
        % 计算从检测点i到P的向量
        vec = P - detectors(i, :);

        % 计算方位角（使用atan2d得到[-180, 180]范围的角度）
        angle_to_P = atan2d(vec(2), vec(1));

        % 转换到[0, 360)范围
        angle_to_P = mod(angle_to_P, 360);

        % 计算扇形的角度范围
        theta_min = mod(azimuths(i) - error, 360);
        theta_max = mod(azimuths(i) + error, 360);

        % 判断是否在扇形内（需要处理跨越0度的情况）
        if theta_min <= theta_max
            % 正常情况：扇形不跨越0度
            % 例如：扇形范围 [44, 46]，点的角度应该在此范围内
            if angle_to_P < theta_min || angle_to_P > theta_max
                is_inside = false;
                return;
            end
        else
            % 跨越0度的情况：扇形范围如 [359, 1]
            % 点的角度应该 >= 359 或 <= 1
            if angle_to_P < theta_min && angle_to_P > theta_max
                is_inside = false;
                return;
            end
        end
    end
end
