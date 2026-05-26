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
    tif_path = fullfile(fpath, [name, '_AQuA2_Movie.tif']);

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
    ov1_img = plt.addLabels(ov1_img, evt1);
    [~, ~, ~, nFr] = size(ov1_img);

    % Write multi-page TIFF; open in ImageJ and set frame interval via
    % Image > Properties to get timestamps.
    imwrite(ov1_img(:,:,:,1), tif_path);
    for fr = 2:nFr
        imwrite(ov1_img(:,:,:,fr), tif_path, 'WriteMode', 'append');
    end
    fprintf('  TIFF: %s\n  fps=%.4f — set frame interval in ImageJ: Image > Properties\n', ...
            tif_path, fps);
end
end
