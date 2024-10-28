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
        # This is a hack -- we need to update the profile when the t_min or t_max changes
        # but we don't want to do it twice and delay_callback is not working properly.
        self._viewer_state.add_callback('t_min', self._update_profile, priority=100000)
        #self._viewer_state.add_callback('t_max', self._update_profile, priority=100000)
        #LinesClass = LinesGL if USE_GL else bqplot.Lines

        #self.line_mark = LinesClass(scales=self.view.scales, x=[], y=[])
    #Profile state does this: computing the profile and caching it
    #
    #@property
    #def profile(self):
    #    self.update_profile()
    #    return self._profile_cache

    def _update_profile(self, force=False, **kwargs):
        print(f"Calling _update_profile...")

    # TODO: we need to factor the following code into a common method.

        if (self.line_mark is None or
                self._viewer_state.x_att is None or
                self.state.attribute is None or
                self.state.layer is None):
            return

        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.
        changed = self.pop_changed_properties()
        print(f"Calling _update_profile with {force=} and {changed=}")    
        if force or any(prop in changed for prop in ('layer', 'x_att', 'attribute',
                                                        'function', 'normalize',
                                                        'v_min', 'v_max',
                                                        'as_steps',
                                                        'x_display_unit', 'y_display_unit',
                                                        't_min', 't_max')):
            self._calculate_profile(reset=force)
            force = True

        if force or any(prop in changed for prop in ('alpha', 'color', 'zorder',
                                                        'visible', 'linewidth')):
            self._update_visual_attributes()


class TimeSeriesLayerSubsetArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
