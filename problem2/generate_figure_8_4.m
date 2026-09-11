%% 生成8.4节固定搜索圆示意图
% 对应论文8.4节的算法描述

clear; clc; close all;

% 添加路径
addpath('utils');
addpath('utils/visualization');

%% 参数设置
% 第一检测点
S1 = [0, 0];

% 第一示向度（度）
theta1 = 45;

% 估计干扰源距离（米）
d0 = 600;

%% 生成图形
fprintf('=== 生成8.4节固定搜索圆示意图 ===\n');
fprintf('参数设置：\n');
fprintf('  第一检测点 S1: (%.1f, %.1f)\n', S1(1), S1(2));
fprintf('  第一示向度 θ1: %.1f°\n', theta1);
fprintf('  估计干扰源距离 d0: %.0f m\n', d0);
fprintf('  固定搜索半径: 600 m\n');
fprintf('  角度采样间隔: 1°\n');
fprintf('  采样点数量: 360\n');

% 确保results目录存在
if ~exist('results', 'dir')
    mkdir('results');
end

% 生成图形
output_file = 'results/figure_8_4_fixed_search_circle.png';
plot_fixed_search_circle(S1, theta1, d0, output_file);

fprintf('\n图片已保存至: %s\n', output_file);
fprintf('=== 完成 ===\n');
