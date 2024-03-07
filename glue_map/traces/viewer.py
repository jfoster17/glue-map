from glue_jupyter.bqplot.scatter.viewer import BqplotScatterView

from .state import TracesViewerState
from .layer_artist import TracesLayerArtist, TracesLayerSubsetArtist
from .state_widgets.viewer_traces import TracesViewerStateWidget
from .state_widgets.layer_traces import TracesLayerStateWidget


class TracesViewer(BqplotScatterView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    is2d = False

    _state_cls = TracesViewerState
    _options_cls = TracesViewerStateWidget
    _data_artist_cls = TracesLayerArtist
    _subset_artist_cls = TracesLayerSubsetArtist
    _layer_style_widget_cls = TracesLayerStateWidget

    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
