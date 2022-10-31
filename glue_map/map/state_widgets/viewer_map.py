from ipywidgets import VBox, Checkbox

from glue_jupyter.widgets.linked_dropdown import LinkedDropdown

__all__ = ['MapViewerStateWidget']


class MapViewerStateWidget(VBox):

    def __init__(self, viewer_state):
        super().__init__()
        
        self.state = viewer_state
        
        self.widget_lon_axis = LinkedDropdown(self.state, 'lon_att', label='lon_att')
        self.widget_lat_axis = LinkedDropdown(self.state, 'lat_att', label='lat_att')
        
        super().__init__([self.widget_lon_axis, self.widget_lat_axis])
