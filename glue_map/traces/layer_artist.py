from glue_jupyter.bqplot.scatter.layer_artist import BqplotScatterLayerArtist
from .state import TracesLayerState

__all__ = ['TracesLayerArtist']

USE_GL = True


class TracesLayerArtist(BqplotScatterLayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)

    
class TracesLayerSubsetArtist(BqplotScatterLayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
