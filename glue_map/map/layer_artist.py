import numpy as np
import bqplot
import json 
import random


from glue.core import BaseData
from glue.core.data import Subset

from glue.core.exceptions import IncompatibleAttribute
from glue.viewers.common.layer_artist import LayerArtist
from glue.utils import color2hex

#from ...link import link, dlink
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
    _layer_state_cls = MapPointsLayerState
    _removed = False
    
    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super(MapPointsLayerArtist, self).__init__(viewer_state,
                                                  layer_state=layer_state,
                                                  layer=layer)
        self.map_layer = None
        self._coords = [], []
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible
        
        self.state.add_global_callback(self._update_presentation)
        self._viewer_state.add_global_callback(self._update_presentation)
        
        self._update_presentation(force=True)

                                              
    def clear(self):
        if self.map_layer is not None:
            self.map.remove_layer(self.map_layer)
            self.map_layer = None
            self._coords = [], []

    def remove(self):
            self._removed = True
            self.clear()

    def redraw(self):
        pass
    
    def update(self):
        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """
        We need to add a new boolean mode -- 
            heatmap: which is the default for large? datasets but does not have a lot of options
            layer_group of circle markers: which can do all the cmap and size stuff
        """
        
        
        if self._removed:
            return
        
        changed = set() if force else self.pop_changed_properties()
        
        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            if self.map_layer is not None:
                self.map.remove_layer(self.map_layer)
                self.map_layer = None
            return
        
        logger.debug("updating Map for points in %s" % self.layer.label)
        
        if self.visible is False:
            if self.map_layer is not None:
                self.map.remove_layer(self.map_layer)
                self.map_layer = None
            return
        
        #if force or 'mode' in changed or self.wwt_layer is None:
        #    self.clear()
        #    force = True

        if force or any(x in changed for x in RESET_TABLE_PROPERTIES):
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

            
            if self.state.size_mode == 'Linear' and self.state.size_att is not None:
                try:
                    size_values = self.layer[self.state.size_att]
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.size_att)
                    return
            else:
                size_values = None
            
            if self.state.color_mode == 'Linear' and self.state.cmap_att is not None:
                try:
                    cmap_values = self.layer[self.state.cmap_att]
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.cmap_att)
                    return
            else:
                cmap_values = None

            self.clear()
            
            if not len(lon):
                return

            data_kwargs = {}

            locs = list(zip(lat,lon))
            self.map_layer = Heatmap(locations=locs, radius=2, blur=1, min_opacity=0.5, 
                                    gradient={0:self.state.color,1:self.state.color})
            self.map.add_layer(self.map_layer)
            
            self._coords = lon, lat


        #if force or 'size' in changed or 'size_mode' in changed or 'size_scaling' in changed:
        #    if self.state.size_mode == 'Linear':
        #        self.map_layer.size_scale = self.state.size_scaling
        #    else:
        #        self.map_layer.size_scale = self.state.size * 5 * self.state.size_scaling
        
        if force or 'color' in changed:
            self.map_layer.gradient = {0:self.state.color, 1:self.state.color}
        
        if force or 'alpha' in changed:
            self.map_layer.min_opacity = self.state.alpha
        
        #if force or 'size_vmin' in changed:
        #    self.map_layer.radius = self.state.size_vmin
        #
        #if force or 'size_vmax' in changed:
        #    self.map_layer.radius = self.state.size_vmax
        
        #if force or 'cmap_vmin' in changed:
        #    self.map_layer.cmap_vmin = self.state.cmap_vmin
        
        #if force or 'cmap_vmax' in changed:
        #    self.map_layer.cmap_vmax = self.state.cmap_vmax
        
        #if force or 'cmap' in changed:
        #    self.map_layer.cmap = self.state.cmap
        
        self.enable()

class MapRegionLayerArtist(LayerArtist):
    """
    LayerArtist to draw on top of a Basemap (.mapfigure is controlled by Viewer State)
    """
    pass
