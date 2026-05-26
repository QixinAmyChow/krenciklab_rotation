"""aqua2kit — Ca²⁺ imaging tools: LIF→TIFF conversion, AQuA2 quantification, plotting."""
from .lif_io import convert as lif_to_tiff, join_tifs, read_fps
from .aqua2_io import parse_csv, find_csv, load as load_aqua2
from .quantify import quantify_samples, condition_summary, to_excel
from .plot import event_count_barplot, plot_dff, plot_event_rate, plot_events_per_frame, plot_cell_event_rates, plot_cell_oscillation_freq, plot_event_trajectories, plot_cell_peakcaller, plot_cell_peakcaller_fc, plot_event_direction_distribution, plot_cell_roi_map
from .utils import inspect_mat, event_intervals, event_fft, assign_events_to_cells, cell_event_rates, cell_oscillation_freq, cell_peakcaller
