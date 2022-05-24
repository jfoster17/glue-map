import ipyleaflet

from glue.logger import logger

from glue_jupyter.view import IPyWidgetView
from glue_jupyter.link import link
from glue_jupyter.utils import float_or_none

from .state import MapViewerState
from .layer_artist import MapRegionLayerArtist, MapPointsLayerArtist
from .state_widgets.layer_map import MapLayerStateWidget
from .state_widgets.viewer_map import MapViewerStateWidget
from .utils import get_geom_type

from glue_jupyter.widgets import LinkedDropdown, Color, Size

from ipywidgets import HBox, Tab, VBox, FloatSlider, FloatText

__all__ = ['IPyLeafletMapViewer']


class PointsLayerStateWidget(VBox):
    def __init__(self, layer_state):
        self.state = layer_state
        self.color_widgets = Color(state=self.state)
        self.size_widgets = Size(state=self.state)
    
        super().__init__([self.size_widgets, self.color_widgets])


class IPyLeafletMapViewer(IPyWidgetView):
    """
    A glue viewer to show an `ipyleaflet` Map viewer with data.
    
    The data can either be regions (using a MapRegionLayerArtist)
    or point-like data (using a MapPointsLayerArtist)
    
    """
    
    
    LABEL = 'Map Viewer (ipleaflet)'
    _map = None # The ipyleaflet Map object
    
    allow_duplicate_data = True
    allow_duplicate_subset = False
    
    _state_cls = MapViewerState
    _options_cls = MapViewerStateWidget 
    _layer_style_widget_cls = {
        MapRegionLayerArtist: PointsLayerStateWidget, # Do our own RegionLayerStateWidget
        MapPointsLayerArtist: PointsLayerStateWidget,
    }

    tools = ['ipyleaflet:pointselect','ipyleaflet:rectangleselect']

    def __init__(self, session, state=None):
        logger.debug("Creating a new Viewer...")
        super(IPyLeafletMapViewer, self).__init__(session, state=state)

        self._initialize_map()
        
        link((self.state, 'zoom_level'), (self._map, 'zoom'), float_or_none)
        link((self.state, 'center'), (self._map, 'center'))

        self.state.add_global_callback(self._update_map)
        self._update_map(force=True)
        self.create_layout()
        
    def _initialize_map(self):
        self._map = ipyleaflet.Map(basemap=self.state.basemap, prefer_canvas=True)
        
    def _update_map(self, force=False, **kwargs):
        if force or 'basemap' in kwargs:
            pass #Change basemap
    
    def get_layer_artist(self, cls, layer=None, layer_state=None):
        """Need to add a reference to the ipyleaflet Map object"""
        return cls(self._map, self.state, layer=layer, layer_state=layer_state)
    
    def get_data_layer_artist(self, layer=None, layer_state=None):
        if get_geom_type(layer) == 'regions':
            cls = MapRegionLayerArtist
        elif get_geom_type(layer) == 'points':
            cls = MapPointsLayerArtist
        else:
            raise ValueErorr(f"IPyLeafletMapViewer does not know how to render the data in {layer.label}")
        return cls(self.state, map=self._map, layer=layer, layer_state=layer_state)
        
    def get_subset_layer_artist(self, layer=None, layer_state=None):
        return self.get_data_layer_artist(layer=layer, layer_state=layer_state)
    
    
    @property
    def figure_widget(self):
        return self._map
    
    def redraw(self):
        pass
    