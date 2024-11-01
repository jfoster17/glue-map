from glue_jupyter.bqplot.profile.layer_artist import BqplotProfileLayerArtist
from .state import TimeSeriesLayerState

__all__ = ['TimeSeriesLayerArtist']


class TimeSeriesLayerArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
        self._viewer_state.add_callback('t_date', self._update_profile, priority=100000)

    def _update_profile(self, force=False, **kwargs):
        """
        This is a copy from glue_jupyter.bqplot.profile.layer_artist.BqplotProfileLayerArtist
        just to add the t_date parameter to the list of properties that trigger the update.
        """
        #print(f"Calling _update_profile...")

        if (self.line_mark is None or
                self._viewer_state.x_att is None or
                self.state.attribute is None or
                self.state.layer is None or
                self._viewer_state.t_date is None):
            return

        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.
        changed = self.pop_changed_properties()
        #print(f"Calling _update_profile with {force=} and {changed=}")    
        if force or any(prop in changed for prop in ('layer', 'x_att', 'attribute',
                                                        'function', 'normalize',
                                                        'v_min', 'v_max',
                                                        'as_steps',
                                                        'x_display_unit', 'y_display_unit',
                                                        't_date')):
            self._calculate_profile(reset=force)
            force = True

        if force or any(prop in changed for prop in ('alpha', 'color', 'zorder',
                                                     'visible', 'linewidth')):
            self._update_visual_attributes()


class TimeSeriesLayerSubsetArtist(TimeSeriesLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
