from glue_jupyter.bqplot.profile.layer_artist import BqplotProfileLayerArtist
from .state import TimeSeriesLayerState
import bqplot
from bqplot_image_gl import LinesGL

__all__ = ['TimeSeriesLayerArtist']

USE_GL = True


class TimeSeriesLayerArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
        LinesClass = LinesGL if USE_GL else bqplot.Lines

        self.line_mark = LinesClass(scales=self.view.scales, x=[], y=[])
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
