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
from ipyleaflet.leaflet import LayerException, LayersControl, CircleMarker, Heatmap, GeoJSON, LayerGroup
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
    
    we are forced to substitute out a whole layer every time we need to update
    
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
        self._markers = [] #These are the layers/markers to be plotted in Individual Points mode
        if self.state.display_mode == 'Individual Points':
            self.map_layer = LayerGroup(layers = self._markers)
        else: # Heatmap is the default
            self.map_layer = Heatmap(locations=self._coords)

        self.map.add_layer(self.map_layer)
        
        self.state.add_global_callback(self._update_presentation)
        self._viewer_state.add_global_callback(self._update_presentation)
        
        self._update_presentation(force=True)
    
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

    def _update_presentation(self, force=False, **kwargs):
        """
        We need to add a new boolean mode -- 
            heatmap: which is the default for large? datasets but does not have a lot of options
            layer_group of circle markers: which can do all the cmap and size stuff
            
        """
        
        #print(f"Updating layer_artist for points in {self.layer.label}")

        if self._removed:
            return
        
        changed = set() if force else self.pop_changed_properties()
        #print(f"These variables have changed: {changed}")

        #print(f"{self.state.color=}")
        
        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            self.clear()
        
        #logger.debug("updating Map for points in %s" % self.layer.label)
        
        if force or 'display_mode' in changed:
            if self.state.display_mode == 'Individual Points':
                self.map.remove_layer(self.map_layer)
                self.map_layer = LayerGroup(layers=self._markers)
                self.map.add_layer(self.map_layer)
            else:
                self.map.remove_layer(self.map_layer)
                self.map_layer = Heatmap(locations=self._coords)
                self.map.add_layer(self.map_layer)

        
        if self.visible is False:
            self.clear()
        else:
            try:
                self.map.add_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass

        if force or any(x in changed for x in ['lon_att','lat_att','display_mode']):
            #print("Inside lat/lon if statement")
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
            if self.state.display_mode == 'Individual Points':
                for lat,lon in self._coords:
                    self._markers.append(CircleMarker(location=(lat, lon), stroke=False, fill_color=color2hex(self.state.color), fill_opacity = self.state.alpha)) #Might want to make this an option. This is not quite right, we should store the current colors in a state var? Otherwise, we do not get the colormap value back when toggling display_mode...
                self.map_layer.layers = self._markers # layers is the attribute here
            else:
                self.map_layer.locations = self._coords

        if force or any(x in changed for x in ['color','color_mode','cmap_att','display_mode','cmap_vmin','cmap_vmax','cmap']):
            print("Updating color")
            if self.state.display_mode == 'Individual Points':
                if self.state.color_mode == 'Linear' and self.state.cmap_att is not None:
                    try:
                        color_values = self.layer[self.state.cmap_att]
                    except IncompatibleAttribute:
                        self.disable_invalid_attributes(self.state.cmap_att)
                        return
                    print("Calculating colors...")

                    if 'cmap_vmin' not in changed and 'cmap_att' in changed:
                        self.state.cmap_vmin = min(color_values)
                    if 'cmap_vmax' not in changed and 'cmap_att' in changed:
                        self.state.cmap_vmax = max(color_values)
                    diff = self.state.cmap_vmax-self.state.cmap_vmin or 1 #to avoid div by zero
                    normalized_vals = (color_values-self.state.cmap_vmin)/diff
                    for marker,val in zip(self._markers,normalized_vals):
                        marker.fill_color = color2hex(self.state.cmap(val))
                else:
                    for marker in self._markers:
                        marker.fill_color = color2hex(self.state.color)


            else:
                try:
                    self.map.remove_layer(self.map_layer)
                    color = color2hex(self.state.color)
                    self.map_layer.gradient = {0:color, 1:color} 
                    self.map.add_layer(self.map_layer)
                except ipyleaflet.LayerException:
                    pass
        
        if force or any(x in changed for x in ['size','size_mode','size_scaling','size_att','display_mode','size_vmin','size_vmax']):
            print("Updating size")
            if self.state.size_mode == 'Linear' and self.state.size_att is not None:
                print("Linear mode is active")
                try:
                    size_values = self.layer[self.state.size_att]
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.size_att)
                    return
                    
                if self.state.display_mode == 'Individual Points':
                    print("Calculating sizes")
                    if 'size_vmin' not in changed and 'size_att' in changed:
                        self.state.size_vmin = min(size_values) # Actually we only want to update this if we swap size_att
                    if 'size_vmax' not in changed and 'size_att' in changed:
                        self.state.size_vmax = max(size_values)
                    diff = self.state.size_vmax-self.state.size_vmin
                    normalized_vals = (size_values-self.state.size_vmin)/diff
                    #print(f'{self._markers=}')
                    #self.map.remove_layer(self.map_layer)
                    for marker,val in zip(self._markers,normalized_vals):
                        marker.radius = int((val + 1)*self.state.size_scaling*5) # So we always show the points
                        #print(int(val)+1)
                #self.map.add_layer(self.map_layer)
                
            else:
                size_values = None
                try:
                    self.map.remove_layer(self.map_layer)
                    self.map_layer.radius = self.state.size * self.state.size_scaling
                    self.map_layer.blur = self.map_layer.radius/10
                    self.map.add_layer(self.map_layer)
                except ipyleaflet.LayerException:
                    pass
                
        if force or 'alpha' in changed:
            try:
                self.map.remove_layer(self.map_layer)
                self.map_layer.min_opacity = self.state.alpha #This is not quite right, but close enough
                self.map.add_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass

        self.enable()

class MapRegionLayerArtist(LayerArtist):
    """
    Display a GeoRegionData datafile on top of a Basemap (.map is controlled by Viewer State)
    

    """
    _layer_state_cls = MapRegionLayerState
    _removed = False

    #We probably have to (if possible) make this actually blank
    _fake_geo_json = {"type":"FeatureCollection",
      "features":[{
          "type":"Feature",
          "id":"DE",
          "properties":{"name":"Delaware"},
          "geometry":{
              "type":"Polygon",
              "coordinates":[[[-75.414089,39.804456],[-75.507197,39.683964],[-75.414089,39.804456]]]
              }
       }]
      }

    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super(MapRegionLayerArtist, self).__init__(viewer_state,
                                                  layer_state=layer_state,
                                                  layer=layer)
        self.map_layer = None
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible
        
        self._regions = self._fake_geo_json
        self.map_layer = GeoJSON(data = self._regions,
                            style={'fillColor': self.state.color,
                                   'fillOpacity':self.state.alpha,
                                    },
                            hover_style={'fillOpacity':self.state.alpha+0.2}
            
        )
        self.map.add_layer(self.map_layer)
        
        self.state.add_global_callback(self._update_presentation)
        self._viewer_state.add_global_callback(self._update_presentation)
        
        self._update_presentation(force=True)
    
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
    
    def _update_presentation(self, force=False, **kwargs):
        """
        """
        
        #print(f"Updating layer_artist for points in {self.layer.label}")
    
        if self._removed:
            return
        
        changed = set() if force else self.pop_changed_properties()
        #print(f"These variables have changed: {changed}")
    
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
    
        # Probably break out the color logic stuff into a separate statement
        if force or any(x in changed for x in ['lon_att','lat_att']):
            # We try to get lat and lon attributes because even though
            # we do not need them for display, we want to ensure
            # that the attributes are linked with other layers
            #print("Inside lat/lon if statement")
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
    
            gdf = GeoPandasTranslator().to_object(self.layer)
            self._regions = json.loads(gdf.to_json())
            self.map_layer.data = self._regions
    
        if force or any(x in changed for x in ['cmap_att','color_mode','cmap','cmap_vmin','cmap_vmax']):
            if self.state.color_mode == 'Linear' and self.state.cmap_att is not None and self.state.cmap is not None:
                try:
                    cmap_values = self.layer[self.state.cmap_att]
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.cmap_att)
                    return
                if 'cmap_vmin' not in changed and 'cmap_att' in changed:
                    self.state.cmap_vmin = min(cmap_values) # Actually we only want to update this if we swap cmap_att, otherwise allow vmin and vmax to change
                if 'cmap_vmax' not in changed and 'cmap_att' in changed:
                    self.state.cmap_vmax = max(cmap_values)
                diff = self.state.cmap_vmax-self.state.cmap_vmin
                normalized_vals = (cmap_values-self.state.cmap_vmin)/diff
                mapping = dict(zip([str(x) for x in self.layer['Pixel Axis 0 [x]']], normalized_vals)) 
            
                def feature_color(feature):
                    feature_name = feature["id"]
                    return {'fillColor': color2hex(self.state.cmap(mapping[feature_name]))}
                
                old_style = self.map_layer.style
                if 'color' in old_style:
                    del old_style['color']
                if 'fillColor' in old_style:
                    del old_style['fillColor']
            
                self.map_layer.style = old_style #We need to blank these https://github.com/jupyter-widgets/ipyleaflet/issues/675#issuecomment-710970550
                self.map_layer.style_callback = feature_color
                
            elif self.state.color_mode == 'Fixed':
                self.map_layer.style = {'color':self.state.color, 'fillColor':self.state.color}
            
        if force or 'color' in changed:
            if self.state.color is not None and self.state.color_mode == 'Fixed':
                self.map_layer.style = {'color':self.state.color, 'fillColor':self.state.color}
                
        if force or 'alpha' in changed:
            if self.state.alpha is not None:
                self.map_layer.style = {'fillOpacity':self.state.alpha}
                self.map_layer.hover_style = {'fillOpacity':self.state.alpha+0.2}

        self.enable()