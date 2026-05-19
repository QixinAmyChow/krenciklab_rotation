function make_avi(results_dir, fps)
%MAKE_AVI  Generate Motion JPEG AVI overlays from existing AQuA2 .mat files.
%
%   make_avi(results_dir)
%   make_avi(results_dir, fps)
%
%   results_dir - directory containing *_results subfolders
%   fps         - (optional) frame rate in Hz; defaults to 1

addpath(genpath('/home/crnlqz/krenciklab/AQuA2-main'));
startup;

if nargin < 2 || isempty(fps)
    fps = 1;
end

fprintf('FPS: %.4f  (%.3f s/frame)\n', fps, 1/fps);

entries = dir(fullfile(results_dir, '*_results'));
entries = entries([entries.isdir]);

if isempty(entries)
    fprintf('No *_results folders found in %s\n', results_dir);
    return
end

for k = 1:numel(entries)
    fpath = fullfile(results_dir, entries(k).name);
    mat_files = dir(fullfile(fpath, '*_AQuA2.mat'));
    if isempty(mat_files)
        fprintf('No .mat in %s — skipping\n', fpath);
        continue
    end

    mat_path = fullfile(fpath, mat_files(1).name);
    [~, stem] = fileparts(mat_files(1).name);
    name = regexprep(stem, '_AQuA2$', '');
    avi_path = fullfile(fpath, [name, '_AQuA2_Movie.avi']);

    fprintf('\n=== %s ===\n', name);
    fprintf('  Loading .mat...\n');
    load(mat_path, 'res');

    opts    = res.opts;
    evt1    = res.evt1;
    datOrg1 = double(res.datOrg1);
    datOrg1 = (datOrg1 - opts.minValueDat1) / (opts.maxValueDat1 - opts.minValueDat1);
    datOrg1 = max(0, min(1, datOrg1));

    fprintf('  Building overlay (%d events)...\n', numel(evt1));
    ov1_img = plt.regionMapWithData(evt1, datOrg1, 0.5, []);
    % Add per-frame event index labels (visible only when event is active).
    ov1_img = plt.addLabels(ov1_img, evt1);
    [H, W, ~, nFr] = size(ov1_img);

    vw = VideoWriter(avi_path, 'Uncompressed AVI');
    vw.FrameRate = fps;
    open(vw);
    cleanupVw = onCleanup(@() close(vw));
    try
        fig = figure('Visible','off', 'Position',[0 0 W H], 'Color','k');
        ax  = axes(fig, 'Position',[0 0 1 1], 'Units','normalized');
        axis(ax, 'off');
        ih  = imshow(ov1_img(:,:,:,1), 'Parent',ax, 'Border','tight');
        th  = text(ax, 6, 14, '', ...
                   'Color','w', 'FontSize',9, 'FontWeight','bold', ...
                   'VerticalAlignment','top', 'Units','pixels', ...
                   'BackgroundColor','k', 'Margin',1);
        for fr = 1:nFr
            set(ih, 'CData', ov1_img(:,:,:,fr));
            set(th, 'String', sprintf('t = %5.1f s', (fr-1)/fps));
            drawnow;
            F = getframe(ax);
            writeVideo(vw, imresize(F.cdata, [H W]));
        end
        close(fig);
    catch ME
        fprintf('  Warning: timestamp overlay skipped (%s)\n', ME.message);
        try; close(fig); catch; end
        for fr = 1:nFr
            writeVideo(vw, ov1_img(:,:,:,fr));
        end
    end
    clear cleanupVw;
    fprintf('  Movie: %s\n', avi_path);
end
end
