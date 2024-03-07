from glue.viewers.scatter.state import ScatterViewerState, ScatterLayerState


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


class TracesLayerState(ScatterLayerState):

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state)
