%% 问题一 随机配置交叉验证 —— MATLAB 管线端
% ==============================================================
% 读取 verify_random_python.py 生成的 inputs.csv，
% 用与 main_problem1.m 完全相同的核心链路求解：
%   边界射线求交 -> point_in_sectors 容差筛选 -> 凸包 -> 旋转卡壳 -> 覆盖圆判定
% 结果写入 mat_results.csv，供 Python 端逐例比对。
%
% 运行： matlab -batch "run('verify_random_matlab.m')"

clear; clc;
addpath('utils');

ang_tol = 1e-9;

T = readcell('inputs.csv', 'Delimiter', ',', 'TextType', 'string');
hdr = T(1, :);
n_row = size(T, 1) - 1;

fid = fopen('mat_results.csv', 'w');
fprintf(fid, 'case_id,nverts,D,R,dmax,cover\n');

n_mismatch_shape = 0;

for r = 1:n_row
    cid = double(T{r + 1, 1});
    n   = double(T{r + 1, 2});
    det_str = char(T{r + 1, 3});
    az_str  = char(T{r + 1, 4});
    angle_err = double(T{r + 1, 5});

    detectors = zeros(n, 2);
    parts = strsplit(det_str, ';');
    for i = 1:n
        v = sscanf(parts{i}, '%f %f');
        detectors(i, :) = v(1:2)';
    end
    az_parts = strsplit(az_str, ';');
    azimuths = zeros(n, 1);
    for i = 1:n
        azimuths(i) = sscanf(az_parts{i}, '%f');
    end

    % ---- 与 main_problem1.m 相同的核心链路 ----
    rays = [];
    rc = 0;
    for i = 1:n
        rc = rc + 1;
        rays(rc).origin = detectors(i, :);
        rays(rc).theta = mod(azimuths(i) - angle_err, 360);
        rays(rc).direction = [cosd(rays(rc).theta), sind(rays(rc).theta)];

        rc = rc + 1;
        rays(rc).origin = detectors(i, :);
        rays(rc).theta = mod(azimuths(i) + angle_err, 360);
        rays(rc).direction = [cosd(rays(rc).theta), sind(rays(rc).theta)];
    end

    candidates = [];
    for i = 1:(rc - 1)
        for j = (i + 1):rc
            [P, ok] = ray_intersection(rays(i).origin, rays(i).direction, ...
                                       rays(j).origin, rays(j).direction);
            if ok
                candidates = [candidates; P];
            end
        end
    end

    valid = [];
    for k = 1:size(candidates, 1)
        if point_in_sectors(candidates(k, :), detectors, azimuths, angle_err, ang_tol)
            valid = [valid; candidates(k, :)];
        end
    end

    if size(valid, 1) < 2
        fprintf(fid, '%d,0,0,0,0,-1\n', cid);
        n_mismatch_shape = n_mismatch_shape + 1;
        continue;
    end

    hull = compute_convex_hull(valid);
    [D, V_p, V_q] = rotating_calipers(hull);

    if D <= 1e-9
        fprintf(fid, '%d,%d,0,0,0,-1\n', cid, size(hull, 1));
        continue;
    end

    C = (V_p + V_q) / 2;
    R = D / 2;
    dmax = 0;
    for k = 1:size(hull, 1)
        dmax = max(dmax, norm(hull(k, :) - C));
    end
    cover = double(dmax <= R + 1e-9 * max(1, D));

    fprintf(fid, '%d,%d,%.10f,%.10f,%.10f,%d\n', ...
            cid, size(hull, 1), D, R, dmax, cover);
end

fclose(fid);
fprintf('MATLAB 端完成：%d 组配置已写入 mat_results.csv\n', n_row);
fprintf('  其中 MATLAB 判为退化(有效顶点<2)的配置数: %d\n', n_mismatch_shape);
