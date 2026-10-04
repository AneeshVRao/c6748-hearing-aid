function save_fig(name)
%SAVE_FIG Save the current figure to results/phase1_matlab/.
d = fullfile(fileparts(mfilename('fullpath')), '..', 'results', 'phase1_matlab');
if ~exist(d, 'dir'), mkdir(d); end
print(gcf, fullfile(d, name), '-dpng', '-r120');
end
