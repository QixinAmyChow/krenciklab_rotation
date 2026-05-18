function run_normcorre(pIn, pOut, skip_patterns)
%RUN_NORMCORRE  Rigid drift correction (NoRMCorre) on a directory of TIFFs.
%
%   run_normcorre(pIn, pOut)
%   run_normcorre(pIn, pOut, skip_patterns)
%
%   pIn           - input TIFF directory (absolute path)
%   pOut          - output directory for corrected TIFFs; created if absent
%   skip_patterns - cell array of filename substrings to skip
%                   (default: {'green_and_red'})

if nargin < 3 || isempty(skip_patterns)
    skip_patterns = {'green_and_red'};
end
if ischar(skip_patterns)
    skip_patterns = {skip_patterns};
end

addpath(genpath('/home/crnlqz/krenciklab/NoRMCorre'));
mkdir(pOut);

files = dir(fullfile(pIn, '*.tif'));

for k = 1:numel(files)
    fname = files(k).name;

    if any(cellfun(@(p) contains(fname, p), skip_patterns))
        fprintf('Skipping: %s\n', fname);
        continue
    end

    fprintf('\n[%d/%d] %s\n', k, numel(files), fname);

    Y = read_file(fullfile(pIn, fname));
    Y = single(Y);
    [d1, d2, ~] = size(Y);

    opts = NoRMCorreSetParms( ...
        'd1',        d1,  ...
        'd2',        d2,  ...
        'bin_width', 200, ...
        'max_shift', 15,  ...
        'us_fac',    50,  ...
        'init_batch',200);

    [Y_mc, shifts, template] = normcorre(Y, opts); %#ok<ASGLU>

    [c_raw, ~, ~] = motion_metrics(Y,    10);
    [c_mc,  ~, ~] = motion_metrics(Y_mc, 10);
    fprintf('  Mean correlation — raw: %.4f  corrected: %.4f\n', mean(c_raw), mean(c_mc));

    out_path = fullfile(pOut, fname);
    Y_mc_u16 = uint16(Y_mc);
    imwrite(Y_mc_u16(:,:,1), out_path);
    for fr = 2:size(Y_mc_u16, 3)
        imwrite(Y_mc_u16(:,:,fr), out_path, 'WriteMode', 'append');
    end
    fprintf('  Saved: %s\n', out_path);

    clear Y Y_mc Y_mc_u16 shifts template c_raw c_mc
end

fprintf('\nNoRMCorre done. Corrected TIFFs in:\n  %s\n', pOut);
end
