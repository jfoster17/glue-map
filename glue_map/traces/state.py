from glue.viewers.scatter.state import ScatterViewerState, ScatterLayerState
from glue.viewers.matplotlib.state import (DeferredDrawSelectionCallbackProperty as DDSCProperty,
                                           DeferredDrawCallbackProperty as DDCProperty)
from glue.core.data_combo_helper import ComponentIDComboHelper

__all__ = ['TracesViewerState', 'TracesLayerState']


TIMEZONE_LOOKUP = {'NYC': 'America/New_York', 
                   'LA': 'America/Los_Angeles',
                   'CHI': 'America/Chicago',
                   'HOU': 'America/Chicago',
                   'DC': 'America/New_York',
                   'BOS': 'America/New_York'}


class TracesViewerState(ScatterViewerState):

    def __init__(self, **kwargs):
        super().__init__()
        self.x_att_helper = ComponentIDComboHelper(self, 'x_att', categorical=False)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', categorical=False)


class TracesLayerState(ScatterLayerState):
    # I feel like all these things should probably be in viewer state


    group_att = DDSCProperty(docstring='Multiple data-points will be grouped by this attribute before plotting.', default_index=-1)
    #I don't think we need this? In general we want to group over x_att
    #agg_att = DDSCProperty(docstring='Attribute to aggregate over (mean) before plotting')

    estimator = DDCProperty('mean', docstring="Function to use to aggregate data points in each group")
    errorbar = DDCProperty('std', docstring="Whether to show error bars [None, 'std', 'sem', 'pi', 'ci']")

    markers_visible = DDCProperty(False, docstring="Whether to show markers")
    line_visible = DDCProperty(True, docstring="Whether to show a line connecting all positions")

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        self.group_att_helper = ComponentIDComboHelper(self, 'group_att', categorical=True)
        #self.agg_att_helper = ComponentIDComboHelper(self, 'agg_att', categorical=True)

        super().__init__(layer=layer, viewer_state=viewer_state, **kwargs)

    def _on_layer_change(self, layer=None):
        super()._on_layer_change(layer=layer)

        #try:
        if self.layer is None:
            self.group_att_helper.set_multiple_data([])
            #self.agg_att_helper.set_multiple_data([])
        else:
            self.group_att_helper.set_multiple_data([self.layer])
            #self.agg_att_helper.set_multiple_data([self.layer])
        # First time around the init function
        # calls something, but we haven't actually 
        #set the 
        #except AttributeError:
        #    pass