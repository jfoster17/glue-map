from glue_jupyter.bqplot.scatter.layer_artist import BqplotScatterLayerArtist
from .state import TracesLayerState
import numpy as np
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.utils import color2hex
from glue.utils import datetime64_to_mpl, ensure_numerical
import pandas as pd
from bqplot_image_gl import LinesGL
import bqplot
from glue_jupyter.utils import float_or_none
from glue_jupyter.utils import colormap_to_hexlist
from glue.viewers.scatter.layer_artist import CMAP_PROPERTIES, MARKER_PROPERTIES, DATA_PROPERTIES
from glue_jupyter.bqplot.compatibility import ScatterGL, LinesGL
from glue_jupyter.bqplot.scatter.scatter_density_mark import GenericDensityMark


__all__ = ['TracesLayerArtist']

USE_GL = True
# By adding group_att to both VISUAL_PROPERTIES and DATA_PROPERTIES, we automatically run
# both the _update_visual_attributes and _update_data methods when group_att changes
CMAP_PROPERTIES = CMAP_PROPERTIES.add('group_att')
DATA_PROPERTIES = DATA_PROPERTIES.add('group_att')


class TracesLayerArtist(BqplotScatterLayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)

        for mark in self.view.figure.marks:
            if isinstance(mark, ScatterGL):
                self.view.figure.marks.remove(mark)
            elif isinstance(mark, bqplot.Lines):
                self.view.figure.marks.remove(mark)
            elif isinstance(mark, LinesGL):
                self.view.figure.marks.remove(mark)
            elif isinstance(mark, GenericDensityMark):
                self.view.figure.marks.remove(mark)

        self.lines_cls = LinesGL if USE_GL else bqplot.Lines
        
        self.line_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.])]
        for line_mark in self.line_marks:
            line_mark.colors = []
            line_mark.opacities = []

        self.view.figure.marks = list(self.view.figure.marks) + self.line_marks


    def _update_data(self):

        try:
            x = ensure_numerical(self.layer[self._viewer_state.x_att].ravel())
            if x.dtype.kind == "M":
                x = datetime64_to_mpl(x)

        except (IncompatibleAttribute, IndexError):
            # The following includes a call to self.clear()
            self.disable_invalid_attributes(self._viewer_state.x_att)
            return
        else:
            self.enable()

        try:
            y = ensure_numerical(self.layer[self._viewer_state.y_att].ravel())
            if y.dtype.kind == "M":
                y = datetime64_to_mpl(y)
        except (IncompatibleAttribute, IndexError):
            # The following includes a call to self.clear()
            self.disable_invalid_attributes(self._viewer_state.y_att)
            return
        else:
            self.enable()

        if self.state.markers_visible:

            self.scatter_mark.x = x.astype(np.float32).ravel()
            self.scatter_mark.y = y.astype(np.float32).ravel()

        else:
            self.scatter_mark.x = []
            self.scatter_mark.y = []

        if self.state.line_visible:

            if self._viewer_state.group_att is not None:
                if isinstance(self.layer, Data):
                    df = self.layer.get_object(pd.DataFrame)
                else:
                    #  Get a dataframe for just the subset
                    df = self.layer.data.get_subset_object(subset_id=self.layer.label, cls=pd.DataFrame)
                gb = df.groupby([self._viewer_state.group_att])
                self.state.num_groups = len(gb)
                # This could cause flickering. Can be just initialize this empty and then create this
                # list with the data inside of it?
                self.line_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.])]*self.state.num_groups

                for line, (name, group) in zip(self.line_marks, gb):
                    y_att = self._viewer_state.y_att.label
                    x_att = self._viewer_state.x_att.label

                    line.x = group[x_att].values.astype(np.float32).ravel()
                    line.y = group[y_att].values.astype(np.float32).ravel()
        else:
            self.line_mark.x = [0.]
            self.line_mark.y = [0.]

    def _update_visual_attributes(self, changed, force=False):

        if not self.enabled:
            return

        if self.state.markers_visible:

            if self.state.cmap_mode == "Fixed" or self.state.cmap_att is None:
                if force or "color" in changed or "cmap_mode" in changed or "fill" in changed:
                    self.scatter_mark.color = None
                    self.scatter_mark.colors = [color2hex(self.state.color)]
                    self.scatter_mark.fill = self.state.fill
            elif force or any(prop in changed for prop in CMAP_PROPERTIES) or "fill" in changed:
                self.scatter_mark.color = ensure_numerical(
                    self.layer[self.state.cmap_att].ravel(),
                )
                self.scatter_mark.fill = self.state.fill
                self.scale_color_scatter.colors = colormap_to_hexlist(
                    self.state.cmap,
                )
                self.scale_color_scatter.min = float_or_none(self.state.cmap_vmin)
                self.scale_color_scatter.max = float_or_none(self.state.cmap_vmax)

            if force or any(prop in changed for prop in MARKER_PROPERTIES):

                if self.state.size_mode == "Fixed" or self.state.size_att is None:
                    self.scatter_mark.default_size = int(
                        self.state.size * self.state.size_scaling,
                    )
                    self.scatter_mark.size = None
                else:
                    self.scatter_mark.default_size = int(self.state.size_scaling * 7)
                    s = ensure_numerical(self.layer[self.state.size_att].ravel())
                    s = ((s - self.state.size_vmin) /
                         (self.state.size_vmax - self.state.size_vmin))
                    np.clip(s, 0, 1, out=s)
                    s *= 0.95
                    s += 0.05
                    s *= self.scatter_mark.default_size
                    self.scatter_mark.size = s ** 2

        # bqplot only supports these for linestyles
        linestyles = ['solid', 'dashed', 'dotted', 'dash_dotted'] * 10

        if self.state.line_visible:
            if force or "color" in changed:
                for line_mark in self.line_marks:
                    # Probably want to change either color of linestyle based on the group
                    line_mark.colors = [color2hex(self.state.color)]
            if force or "linewidth" in changed:
                for line_mark in self.line_marks:
                    line_mark.stroke_width = self.state.linewidth
            if force or "linestyle" in changed:
                for i, line_mark in enumerate(self.line_marks):
                    line_mark.line_style = linestyles[i]

        for mark in [self.scatter_mark]:

            if mark is None:
                continue

            if force or "alpha" in changed:
                mark.opacities = [self.state.alpha]

        for mark in self.line_marks:
            if mark is None:
                continue
            if force or "alpha" in changed:
                mark.opacities = [self.state.alpha]

        if force or "visible" in changed:
            self.scatter_mark.visible = self.state.visible and self.state.markers_visible
            for line_mark in self.line_marks:
                line_mark.visible = self.state.visible and self.state.line_visible
    
class TracesLayerSubsetArtist(BqplotScatterLayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
