function [D, V_p, V_q] = rotating_calipers(hull)
% ROTATING_CALIPERS 使用旋转卡壳算法计算凸包的直径
%
% 输入:
%   hull - 凸包顶点矩阵 m×2（按逆时针排列）
%
% 输出:
%   D - 直径长度（凸包中任意两点之间的最大距离）
%   V_p - 直径对应的第一个端点坐标 [x, y]
%   V_q - 直径对应的第二个端点坐标 [x, y]
%
% 算法原理:
%   旋转卡壳算法通过旋转一对平行线（"卡壳"）扫描凸包，
%   在O(m)时间内找到最远点对，其中m是凸包顶点数。
%
% 关键点:
%   - MATLAB索引从1开始，需要用 mod(..., m) + 1 处理循环索引
%   - 叉积 cross_prod > 0 表示应该继续移动 j 指针

    m = size(hull, 1);

    % 边界情况处理
    if m < 2
        D = 0;
        V_p = hull(1, :);
        V_q = hull(1, :);
        return;
    end

    % 对于小的凸包（顶点数<=3），直接暴力枚举所有点对
    if m <= 3
        D = 0;
        V_p = hull(1, :);
        V_q = hull(1, :);
        for i = 1:m
            for j = (i+1):m
                dist = norm(hull(i, :) - hull(j, :));
                if dist > D
                    D = dist;
                    V_p = hull(i, :);
                    V_q = hull(j, :);
                end
            end
        end
        return;
    end

    % 初始化
    D = 0;              % 最大直径
    V_p = hull(1, :);   % 直径端点1
    V_q = hull(1, :);   % 直径端点2

    % 找初始最远点对（找距离hull(1,:)最远的点）
    j = 1;
    max_dist_init = 0;
    for k = 1:m
        dist_k = norm(hull(k, :) - hull(1, :));
        if dist_k > max_dist_init
            max_dist_init = dist_k;
            j = k - 1;  % 转换为从0开始的索引
        end
    end

    % 遍历凸包的每条边
    for i = 0:(m-1)
        i_idx = mod(i, m) + 1;      % 当前顶点索引（MATLAB从1开始）
        j_idx = mod(j, m) + 1;      % 对偶顶点索引

        % 当前边向量
        i_next_idx = mod(i+1, m) + 1;
        edge = hull(i_next_idx, :) - hull(i_idx, :);

        % 旋转j指针直到不能再增加投影
        % 防止无限循环，最多旋转m次
        for iter = 1:m
            j_next_idx = mod(j+1, m) + 1;
            vec_j = hull(j_next_idx, :) - hull(j_idx, :);

            % 计算叉积判断是否继续旋转
            % cross_prod = edge × vec_j
            cross_prod = edge(1) * vec_j(2) - edge(2) * vec_j(1);

            if cross_prod > 0
                % 继续移动j指针
                j = j + 1;
                j_idx = mod(j, m) + 1;
            else
                % 停止旋转
                break;
            end
        end

        % 计算当前点对的距离
        dist = norm(hull(i_idx, :) - hull(j_idx, :));
        if dist > D
            D = dist;
            V_p = hull(i_idx, :);
            V_q = hull(j_idx, :);
        end
    end
end
