function [P, is_valid] = ray_intersection(O1, D1, O2, D2)
% RAY_INTERSECTION 计算两条射线的交点
%
% 输入:
%   O1 - 射线1的起点 [x1, y1]
%   D1 - 射线1的方向向量 [dx1, dy1]
%   O2 - 射线2的起点 [x2, y2]
%   D2 - 射线2的方向向量 [dx2, dy2]
%
% 输出:
%   P - 交点坐标 [x, y]，若无有效交点则为 [NaN, NaN]
%   is_valid - 布尔值，true表示有效交点，false表示平行或反向
%
% 算法原理:
%   射线1: P = O1 + t1 * D1  (t1 >= 0)
%   射线2: P = O2 + t2 * D2  (t2 >= 0)
%   求解线性方程组，判断 t1 和 t2 是否非负

    % 计算行列式 (D1 × D2)
    delta = D1(1) * D2(2) - D1(2) * D2(1);

    % 判断平行（行列式接近0）
    if abs(delta) < 1e-10
        P = [NaN, NaN];
        is_valid = false;
        return;
    end

    % 计算从 O1 到 O2 的向量
    dx = O2(1) - O1(1);
    dy = O2(2) - O1(2);

    % 求解参数 t1 和 t2
    % t1 = ((O2 - O1) × D2) / (D1 × D2)
    % t2 = ((O2 - O1) × D1) / (D1 × D2)
    t1 = (dx * D2(2) - dy * D2(1)) / delta;
    t2 = (dx * D1(2) - dy * D1(1)) / delta;

    % 判断有效性（两个参数都必须 >= 0，表示交点在两条射线的正向上）
    if t1 >= 0 && t2 >= 0
        P = O1 + t1 * D1;
        is_valid = true;
    else
        P = [NaN, NaN];
        is_valid = false;
    end
end
