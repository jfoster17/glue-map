from .state import TracesLayerState
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.utils import color2hex
import bqplot
from glue.viewers.scatter.layer_artist import CMAP_PROPERTIES, DATA_PROPERTIES, VISUAL_PROPERTIES
from glue_jupyter.bqplot.compatibility import LinesGL
import warnings
from glue.viewers.common.layer_artist import LayerArtist
from glue.core import BaseData
import sys
from glue.utils import defer_draw
__all__ = ['TracesLayerArtist']

USE_GL = False # If True, the subsets show up as too faint with baseline alpha. Otherwise it seems to work now.
# By adding group_att to both VISUAL_PROPERTIES and DATA_PROPERTIES, we update the traces when the group_att changes
CMAP_PROPERTIES.add('group_var')
DATA_PROPERTIES.add('group_var')


class TracesLayerArtist(LayerArtist):

    _layer_state_cls = TracesLayerState

    def __init__(self, view, viewer_state, layer_state=None, layer=None):

        super().__init__(viewer_state, layer_state=layer_state, layer=layer)

        self._viewer_state.add_global_callback(self._update_traces)
        self.state.add_global_callback(self._update_traces)

        self.state.add_callback("zorder", self._update_zorder)

        self.view = view

        # lines
        self.lines_cls = LinesGL if USE_GL else bqplot.Lines
        
        self.line_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.], display_legend=False)]
        for line_mark in self.line_marks:
            line_mark.colors = [color2hex(self.state.color)]
            line_mark.opacities = [self.state.alpha]
        self.error_marks = [self.lines_cls(scales=self.view.scales, x=[0.], y=[0.], display_legend=False)]
        self.view.figure.marks = list(self.view.figure.marks) + self.line_marks + self.error_marks

    def _update_data(self):
        #print("In _update_data")
        if isinstance(self.layer, Data):
            return
        
        if self.state._data_for_display is None:
            #print("No data for display")
            #self.state.reset_data_for_display()
            return

        if self._viewer_state.group_var is not None:

            data_lines = self.state.data_for_display
            #print(f"{data_lines=}")
            marks = self.view.figure.marks[:]
            for line_mark in self.line_marks+self.error_marks:
                marks.remove(line_mark)
            self.line_marks = []
            self.error_marks = []

            linestyles = ['solid', 'dotted', 'dashed', 'dash_dotted'] * 10
            markers = ['circle', 'triangle-down', 'triangle-up', 'square', 'diamond', 'plus'] * 10

            for i, data_line in enumerate(data_lines):
                #print(f"{data_line=}")
                name = data_line['name']
                x_data = data_line['x']
                y_data = data_line['y']
                lo_error = data_line['lo_error']
                hi_error = data_line['hi_error']

                # For a very large number of groups we can't distinguish individual ones
                # So we just plot them all with the same linestyle
                subset_name = self.layer.label
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

    def _calculate_traces(self, reset=False):
        try:
            self._calculate_traces_thread(reset=reset)
        except Exception:
            self._calculate_traces_error(sys.exc_info())
        else:
            self._calculate_traces_postthread()

    def _calculate_traces_thread(self, reset=False):
        # We need to ignore any warnings that happen inside the thread
        # otherwise the thread tries to send these to the glue logger (which
        # uses Qt), which then results in this kind of error:
        # QObject::connect: Cannot queue arguments of type 'QTextCursor'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if reset:
                self.state.reset_cache()
            self.state.reset_data_for_display(update_limits=False)

    def _calculate_traces_postthread(self):
        self._update_data()

    def _calculate_traces_error(self, exc):
        #self.line_mark.visible = False
        self.redraw()
        if issubclass(exc[0], IncompatibleAttribute):
            if isinstance(self.state.layer, BaseData):
                self.disable_invalid_attributes(self.state.attribute)
            else:
                self.disable_incompatible_subset()
        elif issubclass(exc[0], IncompatibleDataException):
            self.disable("Incompatible data")

    def _update_visual_attributes(self, changed, force=False):

        if not self.enabled:
            return

        if force or "color" in changed:
            for line_mark in self.line_marks:
                line_mark.colors = [color2hex(self.state.color)]
            for error_mark in self.error_marks:
                error_mark.fill_colors = [color2hex(self.state.color)]

        for mark in [self.line_marks]:
            if mark is None:
                continue
            if force or "alpha" in changed:
                for line_mark in self.line_marks:
                    line_mark.opacities = [self.state.alpha]
                for error_mark in self.error_marks:
                    error_mark.fill_opacities = [self.state.alpha/8.]
                    error_mark.opacities = [0]

        if force or "visible" in changed:
            for line_mark in self.line_marks:
                line_mark.visible = self.state.visible and self.state.line_visible
                if self.state.num_groups < 10:
                    line_mark.display_legend = line_mark.visible
                else:
                    line_mark.display_legend = False
            for error_mark in self.error_marks:
                error_mark.visible = self.state.visible and self.state.line_visible

        self.redraw()

    def _update_traces(self, force=False, **kwargs):

        if (self.line_marks is None or
                self._viewer_state.y_att is None or
                self.state.layer is None):
            return

        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.

        changed = self.pop_changed_properties()
        #print(f"{changed=}")
        if force or len(changed & DATA_PROPERTIES) > 0:
            #self._calculate_traces()
            self._update_data()
            force = True

        if force or len(changed & VISUAL_PROPERTIES) > 0:
            self._update_visual_attributes(changed, force=force)

    def remove(self):
        marks = self.view.figure.marks[:]
        for line_mark in self.line_marks:
            marks.remove(line_mark)
        self.line_marks = None
        self.view.figure.marks = marks
        return super().remove()

    def clear(self):
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

    @defer_draw
    def update(self):
        self.state.reset_data_for_display()
        self._update_traces(force=True)
        self.redraw()
