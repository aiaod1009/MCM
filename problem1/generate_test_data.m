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

%% 测试用例2：五检测点配置
% 【修正 2026-09-12】误差改回题目规定的 ±1°。
% 原实现把误差放大到 ±5° 才"产生交集"，偏离了题面设定；实际在 ±1° 下
% 五个扇形同样有非空交集，定位区域为一个四边形。
% 四角检测点的示向度指向中心，中心检测点示向度为 0°。
% 注意：中心检测点本身落在其余四个扇形内，因此它自身构成定位区域的一个顶点，
% 这是检验"待判点与检测点重合"这一边界情形（缺陷B5）的关键用例。

detectors = [
    0,    0;     % 检测点1：原点
    200,  0;     % 检测点2：正东200米
    200,  200;   % 检测点3：东北角
    0,    200;   % 检测点4：西北角
    100,  100    % 检测点5：中心
];

% 示向度指向中心区域
azimuths = [
    45;          % 检测点1：指向中心（东北）
    135;         % 检测点2：指向中心（西北）
    225;         % 检测点3：指向中心（西南）
    315;         % 检测点4：指向中心（东南）
    0            % 检测点5：正东方向
];

error = 1;   % 题目规定的误差范围 ±1°

save('test_data/sample_case2.mat', 'detectors', 'azimuths', 'error');
fprintf('测试用例2已生成: test_data/sample_case2.mat\n');
fprintf('检测点数量: %d\n', size(detectors, 1));
fprintf('预期定位区域: 四边形（中心检测点为一个顶点）\n\n');

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

%% 测试用例4：等边三检测点（"圆盖不住"标准反例）
% 【新增 2026-09-12】
% 三个检测点位于半径 300 m 的等边三角形顶点，示向度均指向原点。
% 在 ±1° 误差下定位区域为六边形，直径 D=12.0945 m，
% 但以 D 为直径的圆无法覆盖该区域：顶点到圆心最大距离 6.1389 m > D/2=6.0472 m，
% 超出 0.091640 m（相对超出 1.5154%，该比值与尺度无关）。
% 这是回答"以定位区域直径为直径的圆能否覆盖该区域"的关键反例。

Rr = 300;
detectors = [
    Rr,                0;
    -Rr/2,   Rr*sqrt(3)/2;
    -Rr/2,  -Rr*sqrt(3)/2
];

azimuths = [
    180;    % 指向原点：正西
    300;    % 指向原点
    60      % 指向原点
];

error = 1;

save('test_data/sample_case4_equilateral.mat', 'detectors', 'azimuths', 'error');
fprintf('测试用例4已生成: test_data/sample_case4_equilateral.mat\n');
fprintf('检测点数量: %d\n', size(detectors, 1));
fprintf('预期定位区域: 六边形，D=12.0945 m，覆盖性=不能覆盖\n\n');

fprintf('所有测试数据生成完毕！\n');
