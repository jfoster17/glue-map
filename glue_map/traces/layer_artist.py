from glue_jupyter.bqplot.scatter.layer_artist import BqplotScatterLayerArtist
from .state import TracesLayerState
import numpy as np
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.utils import color2hex
from glue.utils import datetime64_to_mpl, ensure_numerical
import pandas as pd
import bqplot
from glue_jupyter.utils import float_or_none
from glue_jupyter.utils import colormap_to_hexlist
from glue.viewers.scatter.layer_artist import CMAP_PROPERTIES, MARKER_PROPERTIES, DATA_PROPERTIES, VISUAL_PROPERTIES
from glue_jupyter.bqplot.compatibility import ScatterGL, LinesGL
from glue.viewers.scatter.state import ScatterLayerState


__all__ = ['TracesLayerArtist']

USE_GL = False
# By adding group_att to both VISUAL_PROPERTIES and DATA_PROPERTIES, we automatically run
CMAP_PROPERTIES.add('group_att')
DATA_PROPERTIES.add('group_att')


class TracesLayerArtist(BqplotScatterLayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        # Call grandparent init method
        super(BqplotScatterLayerArtist, self).__init__(viewer_state, layer_state=layer_state, layer=layer)

        # Workaround for the fact that the solid line display choice is shown
        # as a dashed line.
        linestyle_display = {'solid': 'solid',
                             'dashed': '– – – – –',
                             'dotted': '· · · · · · · ·',
                             'dashdot': '– · – · – ·'}

        ScatterLayerState.linestyle.set_display_func(self.state, linestyle_display.get)

        # Watch for changes in the viewer state which would require the
        # layers to be redrawn
        self._viewer_state.add_global_callback(self._update_scatter)
        self.state.add_global_callback(self._update_scatter)

        self.state.add_callback("zorder", self._update_zorder)

        self.view = view

        # Scatter points

        self.scale_color_scatter = bqplot.ColorScale()
        self.scales_scatter = dict(
            self.view.scales,
            color=self.scale_color_scatter,
        )

        self.scatter_mark = ScatterGL(scales=self.scales_scatter, x=[0, 1], y=[0, 1])

        # lines
        self.lines_cls = LinesGL if USE_GL else bqplot.Lines
        
        self.line_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.])]
        for line_mark in self.line_marks:
            line_mark.colors = [color2hex(self.state.color)]
            line_mark.opacities = [self.state.alpha]
        self.error_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.])]
        #self.line_mark.colors = [color2hex(self.state.color)]
        #self.line_mark.opacities = [self.state.alpha]
        self.density_mark = None # We need these defined for now, but ideally we remove entirely
        self.vector_mark = None
        self.view.figure.marks = list(self.view.figure.marks) + [self.scatter_mark] + self.line_marks + self.error_marks

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

        #if self.state.line_visible:

        if self._viewer_state.group_att is not None:
            if isinstance(self.layer, Data):
                df = self.layer.get_object(pd.DataFrame)
                subset_name = ""
            else:
                #  Get a dataframe for just the subset
                subset_name = self.layer.label
                df = self.layer.data.get_subset_object(subset_id=subset_name, cls=pd.DataFrame)
            dfg = df.groupby([self._viewer_state.group_att.label])
            self.state.num_groups = len(dfg)
            #print(self.state.num_groups)
            # This could cause flickering. Can be just initialize this empty and then create this
            # list with the data inside of it?
            #import pdb; pdb.set_trace()
            marks = self.view.figure.marks[:]
            for line_mark in self.line_marks+self.error_marks:
                marks.remove(line_mark)
            self.line_marks = []
            self.error_marks = []

            #marks = self.view.figure.marks[:]
            #for error_mark in self.error_marks:
            #    marks.remove(error_mark)

            #for line_mark in self.line_marks:
            #    line_mark.colors = [color2hex(self.state.color)]
            #    line_mark.opacities = [self.state.alpha]
            #self.view.figure.marks = marks + self.line_marks

            #print(self.view.figure.marks)
            #line_ys = []

            linestyles = ['solid', 'dashed', 'dotted', 'dash_dotted'] * 10
            markers = ['circle', 'triangle-down', 'triangle-up', 'square', 'diamond', 'plus'] * 10

            for i, (name, group) in enumerate(dfg):
                y_att = self._viewer_state.y_att.label
                x_att = self._viewer_state.x_att.label

                data = group.groupby([x_att])[y_att].aggregate(self._viewer_state.estimator)
                x_data = data.index.values
                y_data = data.values

                if self._viewer_state.errorbar is not None:
                    if self._viewer_state.errorbar == "std":
                        error = group.groupby([x_att])[y_att].std().values
                        lo_error = y_data - error
                        hi_error = y_data + error
                    elif self._viewer_state.errorbar == "sem":
                        error = group.groupby([x_att])[y_att].sem().values
                        lo_error = y_data - error
                        hi_error = y_data + error

                #lines_data.append(data)
                # For a very large number of groups we can't distinguish individaul ones
                # So we set 
                if self.state.num_groups < 10: 
                    label = name[0]+" "+subset_name.replace("Metro Area", "")+" ("+self._viewer_state.estimator+")"
                    line_mark = self.lines_cls(scales=self.view.scales, x=x_data, y=y_data, display_legend=True, labels=[label])
                    line_mark.colors = [color2hex(self.state.color)]
                    line_mark.opacities = [self.state.alpha]
                    line_mark.line_style = linestyles[i]
                    line_mark.marker = markers[i]
                    if self._viewer_state.errorbar is not None:
                        error_mark = self.lines_cls(scales=self.view.scales, x=x_data, y=[lo_error, hi_error],
                                                    opacities=[0],
                                                    fill='between', 
                                                    fill_opacities=[self.state.alpha/8.], 
                                                    fill_colors=[color2hex(self.state.color)])
                        self.error_marks.append(error_mark)
                else:
                    line_mark = self.lines_cls(scales=self.view.scales, x=x_data, y=y_data)
                    line_mark.colors = [color2hex(self.state.color)]
                    line_mark.opacities = [self.state.alpha]
                    line_mark.line_style = linestyles[0]

                self.line_marks.append(line_mark)
            
            self.view.figure.marks = marks + self.line_marks + self.error_marks

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

        #if self.state.line_visible:
        if force or "color" in changed:
            for line_mark in self.line_marks:
                line_mark.colors = [color2hex(self.state.color)]
            for error_mark in self.error_marks:
                error_mark.fill_colors = [color2hex(self.state.color)]
                # Probably want to change either color of linestyle based on the group
            #self.line_mark.colors = [color2hex(self.state.color)]*self.state.num_groups
        if force or "linewidth" in changed:
            for line_mark in self.line_marks:
                line_mark.stroke_width = self.state.linewidth
            #self.line_mark.stroke_width = self.state.linewidth #[self.state.linewidth]*self.state.num_groups
        #if force or "linestyle" in changed:
        #    for line_mark in self.line_marks:
        #        line_mark.line_style = self.state.linestyle
            #pass
            #line_styles = []
            #for i in range(self.state.num_groups):
            #    line_styles.append(linestyles[i])
            #self.line_mark.line_style = self.state.linestyle #line_styles

        for mark in [self.scatter_mark]:

            if mark is None:
                continue

            if force or "alpha" in changed:
                mark.opacities = [self.state.alpha]
        for mark in [self.line_marks]:
            if mark is None:
                continue
            if force or "alpha" in changed:
                for line_mark in self.line_marks:
                    line_mark.opacities = [self.state.alpha]
                for error_mark in self.error_marks:
                    error_mark.fill_opacities = [self.state.alpha/8.]
                    error_mark.opacities = [0]
            #self.line_mark.opacities = [self.state.alpha]*self.state.num_groups

        if force or "visible" in changed:
            self.scatter_mark.visible = self.state.visible and self.state.markers_visible
            for line_mark in self.line_marks:
                line_mark.visible = self.state.visible and self.state.line_visible
                if self.state.num_groups < 10:
                    line_mark.display_legend = line_mark.visible
                else:
                    line_mark.display_legend = False
            for error_mark in self.error_marks:
                error_mark.visible = self.state.visible and self.state.line_visible

    def _update_scatter(self, force=False, **kwargs):

        if (self.scatter_mark is None
            or self.line_marks is None
            or self._viewer_state.x_att is None
            or self._viewer_state.y_att is None
            or self.state.layer is None
        ):
            return
        #print("Called _update_scatter")
        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.
        changed = self.pop_changed_properties()
        #print(f"{changed=}")
        if force or len(changed & DATA_PROPERTIES) > 0:
            self._update_data()
            force = True

        if force or len(changed & VISUAL_PROPERTIES) > 0:
            self._update_visual_attributes(changed, force=force)

    def remove(self):
        marks = self.view.figure.marks[:]
        marks.remove(self.scatter_mark)
        self.scatter_mark = None
        marks.remove(self.line_mark)
        self.line_mark = None
        self.view.figure.marks = marks
        return super().remove()

    def clear(self):
        if self.scatter_mark is not None:
            self.scatter_mark.x = []
            self.scatter_mark.y = []
        if self.line_marks is not None:
            for line_mark in self.line_marks:
                line_mark.x = [0.]
                line_mark.y = [0.]
        if self.error_marks is not None:
            for error_mark in self.error_marks:
                error_mark.x = [0.]
                error_mark.y = [0.]

    def _update_zorder(self, *args):
        sorted_layers = sorted(self.view.layers, key=lambda layer: layer.state.zorder)
        self.view.figure.marks = [
            item
            for layer in sorted_layers
            for item in (layer.scatter_mark, layer.line_mark)
        ]

#class TracesLayerSubsetArtist(BqplotScatterLayerArtist):
#
#    _layer_state_cls = TracesLayerState
#        
#    def __init__(self, view, viewer_state, layer_state=None, layer=None):
#
#        super().__init__(view, viewer_state, layer_state=layer_state, layer=layer)
