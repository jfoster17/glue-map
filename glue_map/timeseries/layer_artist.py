from glue_jupyter.bqplot.profile.layer_artist import BqplotProfileLayerArtist
from .state import TimeSeriesLayerState
import bqplot
from bqplot_image_gl import LinesGL
from glue_jupyter.link import dlink
from glue.utils import color2hex
__all__ = ['TimeSeriesLayerArtist']

USE_GL = False


class TimeSeriesLayerArtist(BqplotProfileLayerArtist):

    _layer_state_cls = TimeSeriesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):
        super(BqplotProfileLayerArtist, self).__init__(viewer_state, layer_state=layer_state, layer=layer)

        self._viewer_state.add_global_callback(self._update_profile)
        self.state.add_global_callback(self._update_profile)

        self.view = view

        LinesClass = LinesGL if USE_GL else bqplot.Lines
        self.line_mark = LinesClass(scales=self.view.scales)

        self.view.figure.marks = list(self.view.figure.marks) + [self.line_mark]

        dlink((self.state, 'color'), (self.line_mark, 'colors'), lambda x: [color2hex(x)])
        dlink((self.state, 'alpha'), (self.line_mark, 'opacities'), lambda x: [x])

        self.line_mark.colors = [color2hex(self.state.color)]
        self.line_mark.opacities = [self.state.alpha]
        self.line_mark.marker = 'circle'

    def _update_profile(self, force=False, **kwargs):
        """
        This is a copy from glue_jupyter.bqplot.profile.layer_artist.BqplotProfileLayerArtist
        just to add the t_date parameter to the list of properties that trigger the update.
        """
        # print(f"Calling _update_profile...")

        if (self.line_mark is None or
                self._viewer_state.x_att is None or
                self.state.attribute is None or
                self.state.layer is None or
                self._viewer_state.t_date is None):
            return

        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.
        changed = self.pop_changed_properties()
        # print(f"Calling _update_profile with {force=} and {changed=}")
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
