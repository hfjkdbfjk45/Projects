function analyze_strategy(output_dir)
% Analyze CSV exports produced by the Java RaceSimulator (synthetic model).
if nargin < 1
    output_dir = fullfile('output', 'f1');
end
S = readtable(fullfile(output_dir, 'strategy_results.csv'), 'TextType', 'string');
L = readtable(fullfile(output_dir, 'lap_trace.csv'), 'TextType', 'string');
figure('Name', 'F1 strategy analysis', 'Color', 'w');
tiledlayout(2, 1);
nexttile;
x = 1:height(S);
errorbar(x, S.mean_seconds, S.mean_seconds-S.p10_seconds, ...
    S.p90_seconds-S.mean_seconds, 'o', 'LineWidth', 1.5);
xticks(x); xticklabels(S.strategy); xtickangle(15);
xlabel('Pit strategy'); ylabel('Race time (s)');
title('Monte Carlo race times - synthetic assumptions, 10th to 90th percentile'); grid on;
nexttile; hold on;
strategies = unique(L.strategy, 'stable');
for k = 1:numel(strategies)
    rows = L.strategy == strategies(k);
    plot(L.lap(rows), L.lap_seconds(rows), 'DisplayName', strategies(k), 'LineWidth', 1.2);
end
xlabel('Lap number'); ylabel('Lap time including modeled pit loss (s)');
title('Deterministic dry-race traces'); legend('Location', 'best'); grid on;
fprintf('Lowest modeled mean: %s, %.2f s\n', S.strategy(1), S.mean_seconds(1));
end
