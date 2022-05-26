import numpy as np
import bqplot
import json 
import random

from glue.core import BaseData
from glue.core.data import Subset

from glue.core.exceptions import IncompatibleAttribute
from glue.viewers.common.layer_artist import LayerArtist
from glue.utils import color2hex

from glue_jupyter.link import link, dlink
from .state import MapRegionLayerState, MapPointsLayerState
from ..data import GeoRegionData, GeoPandasTranslator

import ipyleaflet
from ipyleaflet.leaflet import LayerException, LayersControl, CircleMarker, Heatmap
from branca.colormap import linear

from glue.utils import defer_draw, color2hex
from glue.logger import logger

__all__ = ['MapRegionLayerArtist', 'MapPointsLayerArtist']


RESET_TABLE_PROPERTIES = ('mode', 'frame', 'lon_att', 'lat_att', 'size_att', 'cmap_att', 'size_mode', 'color_mode')


class MapPointsLayerArtist(LayerArtist):
    """
    Display a collection of points on a map
    
    Because most of the properties of the heatmap do not update dynamically:
    
    https://github.com/jupyter-widgets/ipyleaflet/issues/643
    
    (gradient and radius certainly do not, locations do) 
    
    we are forced to substitute out a whole layer everytime we need to update
    
    """
    
    
    _layer_state_cls = MapPointsLayerState
    _removed = False
    
    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super(MapPointsLayerArtist, self).__init__(viewer_state,
                                                  layer_state=layer_state,
                                                  layer=layer)
        self.map_layer = None
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible
        
        self._coords = []
        self.map_layer = Heatmap(locations=self._coords)
        self.map.add_layer(self.map_layer)
        
        self.state.add_global_callback(self._update_presentation)
        self._viewer_state.add_global_callback(self._update_presentation)
        
        self._update_presentation(force=True, init=True)
    
    def clear(self):
        if self.map_layer is not None:
            try:
                self.map.remove_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass
            #self._initialize_layer()

    def remove(self):
        self._removed = True
        self.clear()

    def redraw(self):
        pass
    
    def update(self):
        self._update_presentation(force=True)

    def _update_presentation(self, force=False, init=False, **kwargs):
        """
        We need to add a new boolean mode -- 
            heatmap: which is the default for large? datasets but does not have a lot of options
            layer_group of circle markers: which can do all the cmap and size stuff
            
        This logic is rather buggy, and only sometimes responds to changes in attributes
        """
        
        #print(f"Updating layer_artist for points in {self.layer.label}")

        if self._removed:
            return
        
        changed = set() if force else self.pop_changed_properties()
        print(f"These variables have changed: {changed}")
        print(f"{force=}")

        #print(f"{self.state.color=}")
        
        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            self.clear()
        
        #logger.debug("updating Map for points in %s" % self.layer.label)
        
        if self.visible is False:
            self.clear()
        else:
            try:
                self.map.add_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass

        if force or any(x in changed for x in ['lon_att','lat_att','color','size','size_scaling','alpha']):
            self.new_map_layer = Heatmap(locations=self._coords)
            self.new_map_layer.radius = self.map_layer.radius
            self.new_map_layer.gradient = self.map_layer.gradient
            self.new_map_layer.min_opacity = self.map_layer.min_opacity
            self.new_map_layer.blur = self.map_layer.blur

        if force or any(x in changed for x in ['lon_att','lat_att']):
            print("Inside lat/lon if statement")
            try:
                lon = self.layer[self._viewer_state.lon_att]
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lon_att)
                return
            
            try:
                lat = self.layer[self._viewer_state.lat_att]
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lat_att)
                return
            
            if not len(lon):
                return

            locs = list(zip(lat,lon))
            self._coords = locs
            self.new_map_layer.locations = self._coords

        if force or 'color' in changed:
            print("Inside color if statement")

            color = color2hex(self.state.color)
            self.new_map_layer.gradient = {0:color, 1:color} 
                
        if force or 'size' in changed or 'size_scaling' in changed:
            print("Inside size if statement")

            self.new_map_layer.radius = self.state.size * self.state.size_scaling
            self.new_map_layer.blur = self.new_map_layer.radius/10
                
        if force or 'alpha' in changed:
            print("Inside alpha if statement")

            self.new_map_layer.min_opacity = self.state.alpha

        try:
            print("Trying to swap out the layers")
            self.map.remove_layer(self.map_layer)
            self.map.add_layer(self.new_map_layer)
        except ipyleaflet.LayerException:
            print(self.new_map_layer)
            pass
        #self.map.substitute_layer(self.map_layer,self.new_map_layer)
        #except ipyleaflet.LayerException:
        #    pass
        
        self.enable()

class MapRegionLayerArtist(LayerArtist):
    """
    LayerArtist to draw on top of a Basemap (.mapfigure is controlled by Viewer State)
    """
    pass
