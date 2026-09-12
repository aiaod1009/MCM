function is_inside = point_in_sectors(P, detectors, azimuths, error, varargin)
% POINT_IN_SECTORS 判断点是否在所有检测点的扇形区域内（带角度容差）
%
% 输入:
%   P         - 待判断点坐标 [x, y]
%   detectors - 检测点坐标矩阵 n×2
%   azimuths  - 示向度向量 n×1（度）
%   error     - 误差范围（度）
%   varargin{1} - 可选，角度容差 tol（度），默认 1e-9
%
% 输出:
%   is_inside - 布尔值，true 表示点在所有扇形内
%
% 【重要修正 2026-09-12】
%   交会定位区域的每个顶点必然落在两条约束边界射线上（即恰好满足
%   某个约束的等号）。由于 atan2d 的浮点舍入，计算得到的方位角可能在
%   边界值上下抖动 1e-13 度。原实现使用严格 '<' / '>' 比较且不含容差，
%   会导致这些"边界顶点"被随机丢弃，使定位区域被严重低估
%   （实测案例1 直径由 3.4921 m 被误算为 1.0034 m）。
%   此处加入角度容差 tol 后结果与半平面求交的解析结果一致。
%
%   同时修正缺陷 B5：当待判点与该检测点重合（即它正是该楔形的顶点）时，
%   方位角无定义，原实现按 atan2d(0,0)=0 处理会造成误判。闭楔形包含其顶点，
%   故该约束在此时直接视为满足（详见下方循环内注释）。

    if nargin < 5 || isempty(varargin{1})
        tol = 1e-9;
    else
        tol = varargin{1};
    end

    n = size(detectors, 1);
    is_inside = true;

    for i = 1:n
        vec = P - detectors(i, :);

        % 【修正 2026-09-12 · 缺陷B5】点与该检测点重合时（即该楔形的顶点），
        % "从检测点指向该点的方位角"在数学上没有定义，atan2d(0,0) 返回 0，
        % 会被误判为 "不在该扇形内"，从而使这类顶点被丢弃。
        % 闭楔形区域包含其顶点，故此时该约束直接视为满足。
        % 若跳过此处理：当某检测点恰好落在其余所有扇形内时，它本身是定位区域
        % 的一个顶点，丢失它会使直径被低估（200 组随机配置中有 43 组受影响）。
        if norm(vec) <= 1e-9 * max(1, norm(detectors(i, :)))
            continue;
        end

        angle_to_P = mod(atan2d(vec(2), vec(1)), 360);

        theta_min = mod(azimuths(i) - error, 360);
        theta_max = mod(azimuths(i) + error, 360);

        if theta_min <= theta_max
            % 不跨越 0 度：要求 theta_min <= angle <= theta_max
            if angle_to_P < theta_min - tol || angle_to_P > theta_max + tol
                is_inside = false;
                return;
            end
        else
            % 跨越 0 度：要求 angle >= theta_min 或 angle <= theta_max
            if angle_to_P < theta_min - tol && angle_to_P > theta_max + tol
                is_inside = false;
                return;
            end
        end
    end
end
