% 搜索使交会角接近90度的d0值
clear; clc;

S1 = [0, 0];
theta1 = 45;
r = 600;  % S2到S1的距离

fprintf('搜索最优d0值，使交会角接近90度\n');
fprintf('S2距离S1固定为%.0f米\n\n', r);

% 搜索d0从10到2000
best_d0 = 0;
best_alpha = 0;
min_diff = 180;

for d0 = 10:10:2000
    S2 = S1 + r * [cosd(theta1 + 90), sind(theta1 + 90)];
    G = S1 + d0 * [cosd(theta1), sind(theta1)];
    theta2 = atan2d(G(2) - S2(2), G(1) - S2(1));
    alpha = abs(theta2 - theta1);
    alpha = min(alpha, 360 - alpha);

    diff = abs(alpha - 90);
    if diff < min_diff
        min_diff = diff;
        best_d0 = d0;
        best_alpha = alpha;
    end

    % 打印一些关键值
    if mod(d0, 100) == 0 || diff < 1
        fprintf('d0=%4d米, 交会角=%.2f度, 差距=%.2f度\n', d0, alpha, diff);
    end
end

fprintf('\n最优结果:\n');
fprintf('d0=%d米, 交会角=%.2f度\n', best_d0, best_alpha);
