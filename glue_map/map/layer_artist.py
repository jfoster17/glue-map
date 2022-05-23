import numpy as np
import bqplot
import json 

from glue.core import BaseData
from glue.core.data import Subset

from glue.core.exceptions import IncompatibleAttribute
from glue.viewers.common.layer_artist import LayerArtist
from glue.utils import color2hex

from glue_jupyter.link import on_change
#from ...link import link, dlink
from .state import MapLayerState
from ..data import GeoRegionData, GeoPandasTranslator

import ipyleaflet
from ipyleaflet.leaflet import LayerException, LayersControl, CircleMarker, Heatmap
from branca.colormap import linear

from glue.utils import defer_draw, color2hex

__all__ = ['IPyLeafletMapLayerArtist']

class IPyLeafletMapLayerArtist(LayerArtist):
    """
    LayerArtist to draw on top of a Basemap (.mapfigure is controlled by Viewer State)
    """
    #large_data_size = 1000
    
    _layer_state_cls = MapLayerState
    
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
    
    
    def __init__(self, mapfigure, viewer_state, layer_state=None, layer=None):

        super(IPyLeafletMapLayerArtist, self).__init__(viewer_state,
                                                         layer_state=layer_state, layer=layer)
        self.layer = layer
        self._viewer_state = viewer_state
        self.mapfigure = mapfigure
        self.state.add_callback('colormap_att', self._on_attribute_change)

        on_change([(self.state, 'colormap_mode', 'colormap_att')])(self._on_colormap_mode_or_att_change)

        self._viewer_state.add_callback('lat_att', self._on_attribute_change)
        self._viewer_state.add_callback('lon_att', self._on_attribute_change)
        self.state.add_callback('colormap_name', self._on_colormap_change)
        self._on_colormap_change()
        
        if self.state.layer_type == 'regions':
            # We need some valid fake data at creation time
            self.layer_artist = ipyleaflet.GeoJSON(data=self._fake_geo_json,
                                                   style={'fillOpacity': 0.5, 
                                                          'dashArray': '5, 5',
                                                          'weight':0.5},
                                                   hover_style={'fillOpacity': 0.95}
                                                )
            
        else:
            self.layer_artist = ipyleaflet.LayerGroup()
        self.layer_artist.name = self.state.name
        #Not all layers have a way to make them visible/invisible. 
        #And the built-in control does something complicated. 
        #Hard to keep these in sync!
        #link((self.state,'visible'), (self.layer_artist,'visible'))
        self.mapfigure.add_layer(self.layer_artist)
        
        #self.colormap_name = 
        #link((self.state, 'colormap_name'), (self.mapfigure.layers[1], 'colormap')) #We need to keep track of the layer?
    
    
    def _on_colormap_mode_or_att_change(self, ignore=None):
        if self.state.colormap_mode == 'Linear' and self.state.colormap_att is not None:
            pass # XXX Need to update this XXX
            #self.scatter.color = self.layer.data[self.state.colormap_att].astype(np.float32).ravel()
        else:
            pass # XXX Need to update this XXX
            #self.scatter.color = None

    
    def _on_colormap_change(self, value=None):
        """
        self.state.colormap_name is a string
        self.colormap is the actual `branca.colormap.LinearColormap` object
        """
        if self.state.colormap_name is None:
            return
        try:
            colormap = getattr(linear,self.state.colormap_name)
        except AttributeError:
            print("attribute error")
            colormap = linear.viridis #We need a default
        self.colormap = colormap
        self.redraw()

    def _on_attribute_change(self, value=None):
        if self.state.colormap_mode == 'Linear' and self.state.colormap_att is None:
            return
            
        if isinstance(self.layer, BaseData):
            layer = self.layer
        else:
            layer = self.layer.data
        if self.state.layer_type == 'regions':
            # TODO -- We need to verify that we should be plotting this
            # i.e. that the lat/lon attributes are appropriately linked/set
            trans = GeoPandasTranslator()
            try:
                gdf = trans.to_object(self.layer)
            except IncompatibleAttribute:
                self.disable_invalid_attributes()
                self.visible = False
                try:
                    # TODO: We do not want to really remove this, we just want to disable it
                    self.mapfigure.remove_layer(self.layer_artist) 
                except:
                    pass
                return
            
            if isinstance(self.layer, Subset):
                new_layer_artist = ipyleaflet.GeoJSON(data=json.loads(gdf.to_json()),
                                                       style={'fillOpacity': 0.5, 
                                                              'dashArray': '0',
                                                              'color': self.get_layer_color(),
                                                              'weight':3},
                                                       hover_style={'fillOpacity': 0.95},
                                                    )
            else:
                c = np.array(layer[self.state.colormap_att].tolist())
                self.state.value_min = min(c)
                self.state.value_max = max(c)
                diff = self.state.value_max-self.state.value_min
                normalized_vals = (c-self.state.value_min)/diff
                mapping = dict(zip([str(x) for x in layer['Pixel Axis 0 [x]']], normalized_vals)) 
                
                def feature_color(feature):
                    feature_name = feature["id"]
                    return {'fillColor': self.colormap_name(mapping[feature_name])}
                
                new_layer_artist = ipyleaflet.GeoJSON(data=json.loads(gdf.to_json()),
                                               style={'fillOpacity': 0.5, 
                                                      'dashArray': '5, 5',
                                                      'weight':0.5},
                                               hover_style={'fillOpacity': 0.95},
                                               style_callback = feature_color,
                                            )
            new_layer_artist.name = self.state.name
            # Swapping out the full layer seems to work better than updating attributes.
            # This is a bit unfortunate since it means we have more work to keep state attributes in sync
            self.mapfigure.substitute_layer(self.layer_artist, new_layer_artist) 
            self.layer_artist = new_layer_artist

        elif self.state.layer_type == 'points':
            #print(self)
            #There are two cases here, a GeoPandas object and a regular table with lat/lon
            #print("Inside layer_type == points")
            if isinstance(self.state.layer, GeoRegionData):
                pass
            else:
                #print("Clearing layers")
                #self.layer_artist.clear_layers()
                #print("Making marker list")
                lats = self.state.layer[self._viewer_state.lat_att]
                lons = self.state.layer[self._viewer_state.lon_att]
                in_color = self.get_layer_color()
                hex_color = color2hex(in_color)
                #print(color)
                #Fast, and generally good, but color options on heatmap are very limited
                locs = list(zip(lats,lons))
                new_layer_artist = Heatmap(locations=locs, radius=2, blur=1, min_opacity=0.5, gradient={0:hex_color,1:hex_color})
                #print("Heatmap made")
                self.mapfigure.substitute_layer(self.layer_artist, new_layer_artist)
                self.layer_artist = new_layer_artist
                    
                #if isinstance(self.layer, Subset):
                #    print(f"Plotting a subset of {len(lats)}")
                    #print(markers)
                
            
        
        #self._on_colormap_change()
        #self.mapfigure.substitute_layer(self.layer_artist, self.new_layer_artist)
        #Update zoom and center?
        
        self.redraw()
        
    def clear(self):
        """Req: Remove the layer from viewer but allow it to be added back."""
        pass
    
    def remove(self):
        """Req: Permanently remove the layer from the viewer."""
        self.redraw()
    
    def update(self):
        """Req: Update appearance of the layer before redrawing. Called when a subset is changed."""
        #print(f"Update called for {self}")
        self._on_attribute_change()
        self.redraw()
                
    def redraw(self):
        """Req: Re-render the plot."""
        pass

