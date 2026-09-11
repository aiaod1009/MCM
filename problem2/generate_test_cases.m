%% 生成问题2测试数据

clear; clc;

% 确保test_data目录存在
if ~exist('test_data', 'dir')
    mkdir('test_data');
end

%% 测试用例1：原点，示向度45°
S1 = [0, 0];
theta1 = 45;
r_range = [300, 800];
alpha_range = [60, 120];
delta_angle = 30;
d0 = 600;

save('test_data/case1.mat', 'S1', 'theta1', 'r_range', 'alpha_range', 'delta_angle', 'd0');
fprintf('测试用例1已生成：test_data/case1.mat\n');

%% 测试用例2：非原点，示向度0°（正东）
S1 = [500, 500];
theta1 = 0;
r_range = [300, 800];
alpha_range = [60, 120];
delta_angle = 30;
d0 = 600;

save('test_data/case2.mat', 'S1', 'theta1', 'r_range', 'alpha_range', 'delta_angle', 'd0');
fprintf('测试用例2已生成：test_data/case2.mat\n');

fprintf('\n所有测试数据生成完毕！\n');
