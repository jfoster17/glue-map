from glue_jupyter.bqplot.profile.viewer import BqplotProfileView

from .state import TimeSeriesViewererState
from .layer_artist import TimeSeriesLayerArtist
from .state_widgets.viewer_timeseries import TimeSeriesViewererStateWidget
from .state_widgets.layer_timeseries import TimeSeriesLayerStateWidget


class TimeSeriesViewer(BqplotProfileView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    is2d = False

    _state_cls = TimeSeriesViewererState
    _options_cls = TimeSeriesViewererStateWidget
    _data_artist_cls = TimeSeriesLayerArtist
    _subset_artist_cls = TimeSeriesLayerArtist
    _layer_style_widget_cls = TimeSeriesLayerStateWidget

    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y',
             'bqplot:xrange']
