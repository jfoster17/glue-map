from glue_jupyter.bqplot.scatter.viewer import BqplotScatterView

from .state import TracesViewerState
from .layer_artist import TracesLayerArtist  #, TracesLayerSubsetArtist
from .state_widgets.viewer_traces import TracesViewerStateWidget
from .state_widgets.layer_traces import TracesLayerStateWidget


class TracesViewer(BqplotScatterView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    is2d = False

    _state_cls = TracesViewerState
    _options_cls = TracesViewerStateWidget
    _data_artist_cls = TracesLayerArtist
    _subset_artist_cls = TracesLayerArtist
    _layer_style_widget_cls = TracesLayerStateWidget

    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.figure.fig_margin = {"top":10, "bottom":60, "left":80, "right":10}
        self.figure.axes[1].label_offset = '50px'

    def _update_subset(self, message):
        #print(f"TracesViewer._update_subset({message=})")
        # IPyWidgetView._update_subset() "cleverly" ignores subset edits
        # that just update the label, but we need these to update the legend
        if message.subset in self._layer_artist_container:
            for layer_artist in self._layer_artist_container[message.subset]:
                layer_artist.update()
            self.redraw()
