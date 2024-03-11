from glue.viewers.scatter.state import ScatterViewerState, ScatterLayerState
from glue.viewers.matplotlib.state import (DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)

__all__ = ['TracesViewerState', 'TracesLayerState']


TIMEZONE_LOOKUP = {'NYC': 'America/New_York', 
                   'LA': 'America/Los_Angeles',
                   'CHI': 'America/Chicago',
                   'HOU': 'America/Chicago',
                   'DC': 'America/New_York',
                   'BOS': 'America/New_York'}


class TracesViewerState(ScatterViewerState):

    group_att = DDCProperty(docstring='Multiple data-points will be grouped by this attribute before plotting.')
    agg_att = DDSCProperty(docstring='Attribute to aggregate over (mean) before plotting')

    def __init__(self, **kwargs):
        super().__init__()


class TracesLayerState(ScatterLayerState):

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state)
