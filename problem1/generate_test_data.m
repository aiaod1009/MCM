%% 生成测试数据
% 为问题1创建测试用例

clear; clc;

% 确保test_data目录存在
if ~exist('test_data', 'dir')
    mkdir('test_data');
end

fprintf('=== 生成测试数据 ===\n\n');

%% 测试用例1：简单三角形配置
% 三个检测点形成三角形，示向度指向中心区域

detectors = [
    0,   0;      % 检测点1：原点
    100, 0;      % 检测点2：正东100米
    50,  80      % 检测点3：东北方向
];

azimuths = [
    45;          % 检测点1示向度：东北方向
    135;         % 检测点2示向度：西北方向
    270          % 检测点3示向度：正南方向
];

error = 1;       % 误差范围±1度

% 保存测试用例1
save('test_data/sample_case1.mat', 'detectors', 'azimuths', 'error');
fprintf('测试用例1已生成: test_data/sample_case1.mat\n');
fprintf('检测点数量: %d\n', size(detectors, 1));
fprintf('预期定位区域: 三个检测点围成的中心区域附近\n\n');

%% 测试用例2：复杂五边形配置
% 五个检测点，更复杂的交会情况

detectors = [
    0,    0;     % 检测点1：原点
    200,  0;     % 检测点2：正东200米
    200,  200;   % 检测点3：东北角
    0,    200;   % 检测点4：西北角
    100,  100    % 检测点5：中心
];

% 调整示向度，使其指向中心区域
azimuths = [
    45;          % 检测点1：指向中心（东北）
    135;         % 检测点2：指向中心（西北）
    225;         % 检测点3：指向中心（西南）
    315;         % 检测点4：指向中心（东南）
    0            % 检测点5：正东方向
];

error = 5;   % 增大误差范围到±5度，以产生交集

% 保存测试用例2
save('test_data/sample_case2.mat', 'detectors', 'azimuths', 'error');
fprintf('测试用例2已生成: test_data/sample_case2.mat\n');
fprintf('检测点数量: %d\n', size(detectors, 1));
fprintf('预期定位区域: 五个检测点约束下的多边形区域\n\n');

%% 测试用例3：极简情况（两个检测点）
% 用于验证基本逻辑

detectors = [
    0,   0;      % 检测点1：原点
    100, 0       % 检测点2：正东100米
];

azimuths = [
    45;          % 检测点1：东北方向
    135          % 检测点2：西北方向
];

error = 1;

% 保存测试用例3
save('test_data/sample_case3_minimal.mat', 'detectors', 'azimuths', 'error');
fprintf('测试用例3已生成: test_data/sample_case3_minimal.mat\n');
fprintf('检测点数量: %d\n', size(detectors, 1));
fprintf('预期定位区域: 四边形（两条射线各自的左右边界交会）\n\n');

fprintf('所有测试数据生成完毕！\n');
