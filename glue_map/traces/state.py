from glue.viewers.scatter.state import ScatterViewerState, ScatterLayerState
from glue.viewers.matplotlib.state import (DeferredDrawSelectionCallbackProperty as DDSCProperty,
                                           DeferredDrawCallbackProperty as DDCProperty)
from glue.core.data_combo_helper import ComponentIDComboHelper
from glue.core import BaseData
from glue.core.data_combo_helper import ManualDataComboHelper

__all__ = ['TracesViewerState', 'TracesLayerState']


class TracesViewerState(ScatterViewerState):

    reference_data = DDSCProperty(docstring='Reference data')
    group_att = DDSCProperty(docstring='Multiple data-points will be grouped by this attribute before plotting.', default_index=-1)
    #I don't think we need this? In general we want to group over x_att
    #agg_att = DDSCProperty(docstring='Attribute to aggregate over (mean) before plotting')

    estimator = DDCProperty('mean', docstring="Function to use to aggregate data points in each group")
    errorbar = DDCProperty('std', docstring="Whether to show error bars [None, 'std', 'sem', 'pi', 'ci']")

    def __init__(self, **kwargs):
        super().__init__()
        self.x_att_helper = ComponentIDComboHelper(self, 'x_att', categorical=False)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', categorical=False)
        self.group_att_helper = ComponentIDComboHelper(self, 'group_att', categorical=True)
        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')

    def _layers_changed(self, *args):
        super()._layers_changed(*args)
        self.group_att_helper.set_multiple_data(self.layers_data)
        self._update_combo_ref_data()
        self._set_reference_data()

    def _set_reference_data(self):
        if self.reference_data is None:
            for layer in self.layers:
                if isinstance(layer.layer, BaseData):
                    self.reference_data = layer.layer
                    return

    def _update_combo_ref_data(self):
        self.ref_data_helper.set_multiple_data(self.layers_data)


class TracesLayerState(ScatterLayerState):

    markers_visible = DDCProperty(False, docstring="Whether to show markers")
    line_visible = DDCProperty(True, docstring="Whether to show a line connecting all positions")

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state, **kwargs)
