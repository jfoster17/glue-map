from glue_jupyter.bqplot.profile.layer_artist import BqplotProfileLayerArtist
from .state import TimeSeriesViewererState

__all__ = ['TimeSeriesLayerArtist']


class TimeSeriesLayerArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesViewererState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(viewer_state, layer_state=layer_state, layer=layer)
