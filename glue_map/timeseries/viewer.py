import bqplot
from bqplot_image_gl import LinesGL
import numpy as np
import pandas as pd

from glue_jupyter.bqplot.profile.viewer import BqplotProfileView

from .state import TimeSeriesViewerState
from .layer_artist import TimeSeriesLayerArtist, TimeSeriesLayerSubsetArtist
from .state_widgets.viewer_timeseries import TimeSeriesViewerStateWidget
from .state_widgets.layer_timeseries import TimeSeriesLayerStateWidget

USE_GL = False


class TimeSeriesViewer(BqplotProfileView):
    """A viewer for displaying time series data using bqplot."""

    inherit_tools = False
    allow_duplicate_data = False
    allow_duplicate_subset = False
    is2d = False

    _state_cls = TimeSeriesViewerState
    _options_cls = TimeSeriesViewerStateWidget
    _data_artist_cls = TimeSeriesLayerArtist
    _subset_artist_cls = TimeSeriesLayerSubsetArtist
    _layer_style_widget_cls = TimeSeriesLayerStateWidget

    # Defining tools here does not seem to override the previously defined tools
    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        LinesClass = LinesGL if USE_GL else bqplot.Lines

        self.scale_x = bqplot.DateScale(allow_padding=True)
        self.axis_x.scale = self.scale_x
        self.scales = {'x': self.scale_x, 'y': self.scale_y}
        # print(self.scales)
        # print(self.state.t_min)
        starting_point = np.array([self.state.t_min, self.state.t_min]).astype('datetime64[ms]')
        self.timemark = LinesClass(scales=self.scales, x=starting_point, y=[-1000, 1000], colors=['gray'], stroke_width=0.3)
        self.figure.marks = list(self.figure.marks) + [self.timemark]
        self._last_limits = (None, None, None, None)
        self.state.add_callback('t_min', self._update_bqplot_limits)
        self.state.add_callback('t_max', self._update_bqplot_limits)

    def _update_bqplot_limits(self, *args):
        # print("In _update_bqplot_limits...")
        if self._last_limits == (self.state.x_min, self.state.x_max,
                                 self.state.y_min, self.state.y_max):
            return

        # NOTE: in the following, the figure will still update twice. There
        # isn't a way around it at the moment and nesting the context managers
        # doesn't change this - at the end of the day, the two scales are
        # separate widgets so will result in two updates.

        if self.state.x_min is not None and self.state.x_max is not None:
            with self.scale_x.hold_sync():
                self.scale_x.min = pd.to_datetime(self.state.x_min).to_numpy()
                self.scale_x.max = pd.to_datetime(self.state.x_max).to_numpy()

        if self.state.y_min is not None and self.state.y_max is not None:
            with self.scale_y.hold_sync():
                self.scale_y.min = float(self.state.y_min)
                self.scale_y.max = float(self.state.y_max)

        self._last_limits = (self.state.x_min, self.state.x_max,
                             self.state.y_min, self.state.y_max)

    # A hack to make subsets not work from the viewer
    # FIXME if we add subset creation objects
    def apply_roi(self, roi, use_current=False):
        pass
