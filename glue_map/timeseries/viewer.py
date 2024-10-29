from glue_jupyter.bqplot.profile.viewer import BqplotProfileView

from .state import TimeSeriesViewerState
from .layer_artist import TimeSeriesLayerArtist, TimeSeriesLayerSubsetArtist
from .state_widgets.viewer_timeseries import TimeSeriesViewerStateWidget
from .state_widgets.layer_timeseries import TimeSeriesLayerStateWidget

import bqplot
from bqplot_image_gl import LinesGL

USE_GL = True


class TimeSeriesViewer(BqplotProfileView):

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
        self.timemark = LinesClass(scales=self.scales, x=[8, 8], y=[-1000, 1000], colors=['gray'], stroke_width=0.3)
        self.figure.marks = list(self.figure.marks) + [self.timemark]


    # A hack to make subsets not work from the viewer
    # FIXME if we add subset creation objects
    def apply_roi(self, roi, use_current=False):
        pass
