function hull = compute_convex_hull(vertices)
% COMPUTE_CONVEX_HULL 计算有效顶点的凸包
%
% 输入:
%   vertices - 有效顶点坐标矩阵 m×2
%
% 输出:
%   hull - 凸包顶点坐标矩阵，按逆时针排列（不包含首尾重复点）
%
% 算法实现:
%   使用MATLAB内置函数convhull计算凸包
%   注意去掉convhull返回的重复首尾点

    % 边界情况处理
    if size(vertices, 1) < 3
        hull = vertices;
        return;
    end

    % 使用MATLAB内置凸包函数
    % K是凸包顶点的索引，按逆时针排列
    K = convhull(vertices(:,1), vertices(:,2));

    % convhull返回的最后一个点是第一个点的重复，需要去掉
    % 例如：K = [1, 3, 5, 1]，去掉最后的1，得到 [1, 3, 5]
    hull = vertices(K(1:end-1), :);
end
