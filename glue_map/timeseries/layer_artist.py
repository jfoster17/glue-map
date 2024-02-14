from glue_jupyter.bqplot.profile.layer_artist import BqplotProfileLayerArtist
from .state import TimeSeriesLayerState

__all__ = ['TimeSeriesLayerArtist']

USE_GL = True


class TimeSeriesLayerArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)

    #Profile state does this: computing the profile and caching it
    #
    #@property
    #def profile(self):
    #    self.update_profile()
    #    return self._profile_cache

    
class TimeSeriesLayerSubsetArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
