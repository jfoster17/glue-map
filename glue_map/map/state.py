import numpy as np

from glue.core import BaseData, Subset, Data

from echo import delay_callback
from glue.viewers.common.state import ViewerState, LayerState

from echo import CallbackProperty, SelectionCallbackProperty, keep_in_sync

from glue.core.exceptions import IncompatibleAttribute, IncompatibleDataException
from glue.core.state_objects import StateAttributeLimitsHelper

from glue.core.data_combo_helper import ComponentIDComboHelper, ComboHelper
from glue.utils import defer_draw, datetime64_to_mpl
from glue.utils.decorators import avoid_circular
from ipyleaflet import Map, basemaps, basemap_to_tiles

from glue.config import colormaps
from branca.colormap import linear
from glue.core.data import Subset

from ..data import GeoRegionData

__all__ = ['MapViewerState', 'MapRegionLayerState', 'MapPointsLayerState']


class MapViewerState(ViewerState):
    """
    A state class that manages the display of an ipyleaflet Map object:
    https://ipyleaflet.readthedocs.io/en/latest/api_reference/map.html
    which serves as the base for a MapViewer.
    
    lat_att : `~glue.core.component_id.ComponentID`
        The attribute to display as latitude. For choropleth-type data this is a special coordinate component.
    lon_att : `~glue.core.component_id.ComponentID`
        The attribute to display as longitude. For choropleth-type data this is a special coordinate component.
    
    """
    
    center = CallbackProperty((40, -100),docstring='(Lon, Lat) at the center of the map')
    zoom_level = CallbackProperty(4, docstring='Zoom level for the map')
    
    lon_att = SelectionCallbackProperty(default_index=1, docstring='The attribute to display as longitude')
    lat_att = SelectionCallbackProperty(default_index=0, docstring='The attribute to display as latitude')
    
    basemap = CallbackProperty(basemaps.Esri.WorldImagery)

    def __init__(self, **kwargs):

        super(MapViewerState, self).__init__()
        self.lat_att_helper = ComponentIDComboHelper(self, 'lat_att', 
                                                    numeric=True,
                                                    pixel_coord=True, 
                                                    world_coord=True, 
                                                    datetime=False, 
                                                    categorical=False)
        
        self.lon_att_helper = ComponentIDComboHelper(self, 'lon_att', 
                                                    numeric=True,
                                                    pixel_coord=True, 
                                                    world_coord=True, 
                                                    datetime=False, 
                                                    categorical=False)
        
        
        self.add_callback('layers', self._on_layers_changed)
        self._on_layers_changed()
        self.update_from_dict(kwargs)

    def _on_layers_changed(self, *args):
        self.lon_att_helper.set_multiple_data(self.layers_data)
        self.lat_att_helper.set_multiple_data(self.layers_data)

class MapRegionLayerState(LayerState):
    pass

class MapPointsLayerState(LayerState):
    """
    A state class for displaying points on a map.
    """
    
    layer = CallbackProperty()
    color = CallbackProperty()
    size = CallbackProperty()
    alpha = CallbackProperty()
    
    size_mode = SelectionCallbackProperty(default_index=0)
    size = CallbackProperty()
    size_att = SelectionCallbackProperty()
    size_vmin = CallbackProperty()
    size_vmax = CallbackProperty()
    size_scaling = CallbackProperty(1)
    
    color_mode = SelectionCallbackProperty(default_index=0)
    cmap_att = SelectionCallbackProperty()
    cmap_vmin = CallbackProperty()
    cmap_vmax = CallbackProperty()
    cmap = CallbackProperty()
    cmap_mode = color_mode
    
    size_limits_cache = CallbackProperty({})
    cmap_limits_cache = CallbackProperty({})

    name = "" #Name for display in the 
    
    def __init__(self, layer=None, **kwargs):
        
        self._sync_markersize = None

        super(MapPointsLayerState, self).__init__(layer=layer)
        
        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')
        self._sync_size = keep_in_sync(self, 'size', self.layer.style, 'markersize')

        self.color = self.layer.style.color
        self.size = self.layer.style.markersize
        self.alpha = self.layer.style.alpha

        self.size_att_helper = ComponentIDComboHelper(self, 'size_att',
                                                      numeric=True,
                                                      categorical=False)
        self.cmap_att_helper = ComponentIDComboHelper(self, 'cmap_att',
                                                      numeric=True,
                                                      categorical=False)

        self.size_lim_helper = StateAttributeLimitsHelper(self, attribute='size_att',
                                                          lower='size_vmin', upper='size_vmax',
                                                          cache=self.size_limits_cache)
        
        self.cmap_lim_helper = StateAttributeLimitsHelper(self, attribute='cmap_att',
                                                          lower='cmap_vmin', upper='cmap_vmax',
                                                          cache=self.cmap_limits_cache)
        
        self.add_callback('layer', self._on_layer_change)
        if layer is not None:
            self._on_layer_change()

        self.cmap = colormaps.members[0][1]

        MapPointsLayerState.color_mode.set_choices(self,['Fixed', 'Linear'])
        MapPointsLayerState.size_mode.set_choices(self,['Fixed', 'Linear'])

        if isinstance(layer, Subset):
            self.name = f"{self.name} {(self.layer.data.label)}"
        
        self.update_from_dict(kwargs)

            
        
    def _on_layer_change(self, layer=None):
        with delay_callback(self, 'cmap_vmin', 'cmap_vmax', 'size_vmin', 'size_vmax'):
            if self.layer is None:
                self.cmap_att_helper.set_multiple_data([])
                self.size_att_helper.set_multiple_data([])
            else:
                self.cmap_att_helper.set_multiple_data([self.layer])
                self.size_att_helper.set_multiple_data([self.layer])
        
    def _on_attribute_change(self, *args):
        #print("In _on_attribute_change")
        #print(self.layer)
        if self.layer is not None:
            self.color_att_helper.set_multiple_data([self.layer])

    def _layer_changed(self):
            
        super(MapPointsLayerState, self)._layer_changed()
    
        if self._sync_markersize is not None:
            self._sync_markersize.stop_syncing()
    
        if self._sync_color is not None:
            self._sync_color.stop_syncing()

        if self.layer is not None:
            self.size = self.layer.style.markersize
            self._sync_markersize = keep_in_sync(self, 'size', self.layer.style, 'markersize')
    
            self.color = self.layer.style.color
            self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')

    
    def flip_size(self):
        self.size_lim_helper.flip_limits()
    
    def flip_cmap(self):
        self.cmap_lim_helper.flip_limits()

    
    @property
    def viewer_state(self):
        return self._viewer_state

    @viewer_state.setter
    def viewer_state(self, viewer_state):
        self._viewer_state = viewer_state

