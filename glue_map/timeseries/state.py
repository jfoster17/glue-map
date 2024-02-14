from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.core.data import Data

__all__ = ['TimeSeriesViewerState', 'TimeSeriesLayerState']


class TimeSeriesViewerState(ProfileViewerState):
    pass


class TimeSeriesLayerState(ProfileLayerState):

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state)
        if isinstance(layer, Data):
            #  This makes a data layer invisible at the start
            # This is not what we want if we are restoring a session
            # And turning the layer visible for the first time does
            # not refresh the zoom of the plot to show the new profile
            # data
            self.visible = False
