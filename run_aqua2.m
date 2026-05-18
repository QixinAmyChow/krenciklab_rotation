function run_aqua2(pIn, pOut, lif_path)
%RUN_AQUA2  Batch AQuA2 Ca2+ event detection on motion-corrected TIFFs.
%
%   run_aqua2(pIn, pOut)
%   run_aqua2(pIn, pOut, lif_path)
%
%   pIn      - input TIFF directory (NoRMCorre-corrected)
%   pOut     - output directory; one *_results subfolder is created per file
%   lif_path - (optional) path to source .lif file; FrameTime attribute sets
%              AVI frame rate.  Omit or pass '' to default to fps = 1.

if nargin < 3
    lif_path = '';
end

close all;

addpath(genpath('/home/crnlqz/krenciklab/AQuA2-main'));
startup;

mkdir(pOut);

batchSet.propMetric         = true;
batchSet.networkFeatures    = true;
batchSet.outputMovie        = true;
batchSet.outputFeatureTable = true;

% --- Read acquisition frame rate from LIF metadata ---
if ~isempty(lif_path) && isfile(lif_path)
    fps = readLifFps(lif_path);
    fprintf('FPS from LIF: %.4f  (%.3f s/frame)\n', fps, 1/fps);
else
    fps = 1;
    if ~isempty(lif_path)
        fprintf('Warning: LIF file not found (%s); assuming fps=1\n', lif_path);
    else
        fprintf('No LIF file provided; assuming fps=1\n');
    end
end

p_cell     = '';
p_landmark = '';
bd = containers.Map;
bd('None') = [];

files_tif  = dir(fullfile(pIn, '*.tif'));
files_tiff = dir(fullfile(pIn, '*.tiff'));
files_mat  = dir(fullfile(pIn, '*.mat'));
files = [files_tif; files_tiff; files_mat];

for xxx = 1:numel(files)
    f1 = files(xxx).name;
    fprintf('\n=== [%d/%d] %s ===\n', xxx, numel(files), f1);

    opts = util.parseParam_for_batch(xxx);
    opts.singleChannel = true;
    opts.whetherExtend = true;
    opts.propMetric      = batchSet.propMetric;
    opts.networkFeatures = batchSet.networkFeatures;

    disp('  Loading...');
    [datOrg1, datOrg2, opts] = burst.prep1(pIn, f1, pIn, [], [], opts);
    opts.singleChannel = isempty(datOrg2);

    if opts.bleachCorrect == 2
        datOrg1 = pre.bleach_correct(datOrg1);
    elseif opts.bleachCorrect == 3
        datOrg1 = pre.bleach_correct2(datOrg1, opts);
    end
    opts.sz = size(datOrg1);

    evtSpatialMask = true(opts.sz(1:3));
    disp('  Baseline & noise estimation...');
    [dF1, opts] = pre.baselineRemoveAndNoiseEstimation(datOrg1, opts, evtSpatialMask, 1, []);
    opts.maxdF1 = min(100, max(dF1(:)));
    dF2 = []; datOrg2 = [];

    disp('  Active region detection...');
    arLst1 = act.acDetect(dF1, opts, evtSpatialMask, 1, []);
    arLst2 = [];

    disp('  Temporal segmentation...');
    opts.step = 0.5;
    [seLst1, subEvtLst1, seLabel1, majorInfo1, opts, sdLst1, ~, ~] = ...
        se.seDetection(dF1, datOrg1, arLst1, opts, []);
    seLst2 = []; subEvtLst2 = [];

    disp('  Spatial segmentation...');
    [riseLst1, datR1, evt1, ~] = evt.se2evtTop(dF1, seLst1, subEvtLst1, seLabel1, majorInfo1, opts, []);
    evt2 = []; datR2 = []; riseLst2 = [];

    gloEvt1 = []; gloDatR1 = []; gloRiseLst1 = [];
    gloEvt2 = []; gloDatR2 = []; gloRiseLst2 = [];
    ftsGlo1 = []; ftsGlo2 = []; dffAlignedMatGlo1 = []; dffAlignedMatGlo2 = [];

    disp('  Feature extraction...');
    opts.stdMapOrg    = opts.stdMapOrg1;
    opts.maxValueDat  = opts.maxValueDat1;
    opts.minValueDat  = opts.minValueDat1;
    opts.tempVarOrg   = opts.tempVarOrg1;
    opts.correctPars  = opts.correctPars1;
    [fts1, dffMat1, dMat1, dffAlignedMat1] = fea.getFeaturesTop(datOrg1, evt1, opts, []);
    fts1.channel = 1;
    fts2 = []; dffMat2 = []; dMat2 = []; dffAlignedMat2 = [];

    if opts.propMetric
        fts1 = fea.getFeaturesPropTop(datR1, evt1, fts1, opts);
    end

    if opts.networkFeatures
        btSt.filterMsk1 = true(numel(evt1), 1);
        btSt.filterMsk2 = true(numel(evt2), 1);
        fts1 = fea.getNetworkFeatures(datR1, evt1, fts1, btSt, bd, opts, 1);
    end

    disp('  Saving...');
    vSave = {'opts','ov','datOrg1','datOrg2','evt1','evt2','fts1','fts2', ...
             'dffMat1','dMat1','dffMat2','dMat2','riseLst1','riseLst2', ...
             'dF1','dF2','gloEvt1','gloEvt2','ftsGlo1','ftsGlo2', ...
             'gloRiseLst1','gloRiseLst2'};

    ov = containers.Map('UniformValues', 0);
    ov('None') = [];
    ov1 = ui.over.getOv([], evt1, opts.sz, datR1, 1);
    ov1.name = 'Events'; ov1.colorCodeType = {'Random'};
    ov('Events_Red') = ov1;
    ov2 = ui.over.getOv([], evt2, opts.sz, datR2, 2);
    ov2.name = 'Events'; ov2.colorCodeType = {'Random'};
    ov('Events_Green') = ov2;

    res = [];
    for ii = 1:numel(vSave)
        res.(vSave{ii}) = eval(vSave{ii});
    end
    res.datOrg1 = uint16(res.datOrg1 * (opts.maxValueDat1 - opts.minValueDat1) + opts.minValueDat1);
    res.stg.post = 1; res.stg.detect = 1;
    res.bd = bd; res.maxVal = opts.maxValueDat1;

    name = erase(f1, {'.tiff', '.tif', '.mat'});
    fpath = fullfile(pOut, [name, '_results']);
    mkdir(fpath);
    save(fullfile(fpath, [name, '_AQuA2.mat']), 'res', '-v7.3', '-nocompression');

    if batchSet.outputFeatureTable
        lmkLst = [];
        fname_base = [name, '_AQuA2'];
        ftTb1 = fea.getFeatureTable00(fts1, lmkLst, []);
        writetable(ftTb1, fullfile(fpath, [fname_base, '_Ch1.csv']), ...
                   'WriteVariableNames', 0, 'WriteRowNames', 1);
        fea.outputCurves(dffAlignedMat1, fts1, dffAlignedMat2, fts2, opts, fpath, fname_base);
        fea.outputRegions(fts1, ftTb1, [], fts2, [], [], bd, opts, fpath, fname_base);
        fea.outputRisingMap([], [], riseLst1, 1:numel(riseLst1), riseLst2, 1:numel(riseLst2), ...
                            opts, fpath, [fname_base, '_risingMaps']);
    end

    if batchSet.outputMovie
        ov1_img = plt.regionMapWithData(evt1, datOrg1, 0.5, datR1);
        [H, W, ~, nFr] = size(ov1_img);
        avi_path = fullfile(fpath, [name, '_AQuA2_Movie.avi']);
        vw = VideoWriter(avi_path, 'Uncompressed AVI');
        vw.FrameRate = fps;
        open(vw);
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
            for fr = 1:nFr
                writeVideo(vw, ov1_img(:,:,:,fr));
            end
        end
        close(vw);
        fprintf('  Movie: %s\n', avi_path);
    end

    % Label map: uint16 TIFF, pixel value = 1-based event index.
    % Open in Fiji with glasbey LUT; use Analyze > Analyze Particles to
    % overlay numeric labels via the ROI Manager.
    H = opts.sz(1); W = opts.sz(2);
    lblMap = zeros(H, W, 'uint16');
    for nn = 1:numel(evt1)
        pix = evt1{nn};
        if numel(opts.sz) == 3
            [row_lbl, col_lbl, ~] = ind2sub(opts.sz, pix);
        else
            [row_lbl, col_lbl, ~, ~] = ind2sub(opts.sz, pix);
        end
        idx2d = sub2ind([H, W], row_lbl(:), col_lbl(:));
        lblMap(unique(idx2d)) = uint16(nn);
    end
    imwrite(lblMap, fullfile(fpath, [name, '_label_map.tif']));

    fprintf('  Done: %s\n', fpath);
    clear datOrg1 datOrg2 dF1 dF2 evt1 evt2 fts1 fts2 res ov
end

fprintf('\nAQuA2 batch complete. Results in:\n  %s\n', pOut);
end

% -------------------------------------------------------------------------
function fps = readLifFps(lif_path)
% Read acquisition frame rate from a Leica LIF file's embedded XML header.
    fid = fopen(lif_path, 'rb');
    raw = fread(fid, 1e6, 'uint8=>uint8');
    fclose(fid);

    % Locate '<LMS' in UTF-16LE: bytes 3C 00 4C 00 4D 00 53 00
    n   = numel(raw);
    hit = raw(1:n-7)==0x3C & raw(2:n-6)==0x00 & raw(3:n-5)==0x4C & ...
          raw(4:n-4)==0x00 & raw(5:n-3)==0x4D & raw(6:n-2)==0x00 & ...
          raw(7:n-1)==0x53 & raw(8:n  )==0x00;
    xs = find(hit, 1);
    if isempty(xs)
        fps = 1;
        warning('readLifFps: XML marker not found in %s; defaulting to fps=1', lif_path);
        return;
    end

    nbytes    = n - xs + 1;
    nbytes    = nbytes - mod(nbytes, 2);
    xml_bytes = raw(xs : xs + nbytes - 1);
    xml_str   = native2unicode(xml_bytes', 'UTF-16LE');

    tok = regexp(xml_str, 'FrameTime="([\d.E+\-]+)"', 'tokens', 'once');
    if ~isempty(tok)
        fps = 1 / str2double(tok{1});
    else
        fps = 1;
        warning('readLifFps: FrameTime not found in %s; defaulting to fps=1', lif_path);
    end
end
