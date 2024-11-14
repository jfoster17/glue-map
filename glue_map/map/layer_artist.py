import json
import random

import ipyleaflet
import numpy as np
from glue.core.exceptions import IncompatibleAttribute
from glue.core.data import Data
from glue.utils import color2hex, ensure_numerical
from glue.viewers.common.layer_artist import LayerArtist
from glue_jupyter.link import link
from ipyleaflet import CircleMarker, GeoJSON, Heatmap, LayerGroup, ImageOverlay, ImageService, Polygon
import matplotlib.pyplot as plt
import PIL
import PIL.Image
from io import BytesIO
from base64 import b64encode
import rasterio
from rasterio import Affine as A
from rasterio.warp import reproject, Resampling
from time import time
from glue.core.data_derived import IndexedData

from ..data import GeoPandasTranslator, RemoteGeoData_ArcGISImageServer
from .state import MapPointsLayerState, MapRegionLayerState, MapXarrayLayerState, MapImageServerLayerState
# from glue.logger import logger


# my_logger = logging.getLogger("")
# my_logger.setLevel(logging.WARNING)

__all__ = ["MapRegionLayerArtist", "MapPointsLayerArtist", "MapXarrayLayerArtist", "MapImageServerLayerArtist"]


RESET_TABLE_PROPERTIES = (
    "mode",
    "frame",
    "lon_att",
    "lat_att",
    "size_att",
    "cmap_att",
    "size_mode",
    "color_mode",
)


class MapImageServerSubsetLayerArtist(LayerArtist):
    """
    Display a spatial(?) subset of an image from an ESRI ImageServer
    """
    _layer_state_cls = MapImageServerLayerState
    _removed = False

    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super().__init__(
            viewer_state, layer_state=layer_state, layer=layer
        )
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        #self.visible = self.state.visible 
        self.polygon_layer = Polygon(locations=[[[0, 0], [0, 0], [0, 0]]],
                                     fill_color="blue",
                                     fill_opacity=0.5,
                                     weight=0)
        self.map.add(self.polygon_layer)
        self.state.add_global_callback(self.update)

    def update(self, **kwargs):
        if (
            self.map is None
            or self.state.layer is None
            or self._viewer_state.lat_att is None
            or self._viewer_state.lon_att is None
        ):
            return
        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """ """
        #print("Calling _update_presentation...")
        if self._removed:
            return

        changed = self.pop_changed_properties()

        if self.visible is False:
            self.clear()
        #print(f"{changed}")
        #print(self.layer.subset_state)
        # Hack to not do this the first time _update_presentation
        # is called during subset creation. Should figure out a better
        # check. We NEED the correct subset_state (RoiSubsetState)
        # to get the polygon, but we don't have this the first time
        # this is called.
        if len(list(changed)) > 6:
            return
        try:
            x,y = self.layer.subset_state.roi.to_polygon()
            self.polygon_layer.locations = list(zip(y, x))
            self.polygon_layer.fill_color = self.state.layer.style.color
            self.polygon_layer.fill_opacity = self.state.layer.style.alpha-0.3
            self.enable()

        except:
            self.disable_incompatible_subset()
        #self.polygon_layer.color = self.state.color
        #self.polygon_layer.opacity = self.state.opacity
        #elf.polygon_layer.visible = self.state.visible

    def clear(self):
        if self.polygon_layer is not None:
            try:
                self.map.remove(self.polygon_layer)
            except ipyleaflet.LayerException:
                pass


class MapImageServerLayerArtist(LayerArtist):
    """
    Display an image from an Esri ImageServer
    """
    _layer_state_cls = MapImageServerLayerState
    _removed = False

    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super().__init__(
            viewer_state, layer_state=layer_state, layer=layer
        )
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        #self.visible = self.state.visible 
        self.imageserver_layer = ImageService()
        self.map.add(self.imageserver_layer)
        self.state.add_global_callback(self.update)

    def update(self, **kwargs):
        if (
            self.map is None
            or self.state.layer is None
            or self._viewer_state.lat_att is None
            or self._viewer_state.lon_att is None
        ):
            return
        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """ """
        if self._removed:
            return

        changed = self.pop_changed_properties()

        if self.visible is False:
            self.clear()

        if force or any(x in changed for x in ["timestep", "colorscale", "opacity", "data_att"]):
            if isinstance(self.layer, RemoteGeoData_ArcGISImageServer):
                #print(f"{self.state.colorscale=}")
                self.imageserver_layer.time = self.layer.get_time(self.state.timestep, 3828417352000) # FIXME: just some large value
                self.imageserver_layer.rendering_rule = self.layer.get_rendering_rule(self.state.colorscale)
                # Because traitlet Dicts are not eventful, changing the rendering_rule dict
                # does not automatically update the map. As a hack we set the attribution
                # string to force an update. We will have to do this for ANY changes to the 
                # rendering_rule, perhaps concatenating the params for the attribution string.
                if any(x in changed for x in ['colorscale']):
                    self.imageserver_layer.attribution = self.state.colorscale

                self.imageserver_layer.opacity = self.state.opacity
                self.imageserver_layer.url = self.layer.get_image_url(self.state.data_att)
            else:
                # Do something for a subset
                pass

        self.imageserver_layer.visible = self.state.visible

        self.enable()


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
        super(MapPointsLayerArtist, self).__init__(
            viewer_state, layer_state=layer_state, layer=layer
        )
        self.map_layer = None
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible

        self._coords = []
        self._markers = (
            []
        )  # These are the layers/markers to be plotted in Individual Points mode
        if self.state.display_mode == "Individual Points":
            self.map_layer = LayerGroup(layers=self._markers)
        else:  # Heatmap is the default
            self.map_layer = Heatmap(locations=self._coords)

        self.map.add_layer(self.map_layer)

        self.state.add_global_callback(self._update_presentation)
        # self._viewer_state.add_global_callback(self._update_presentation)

        # self._update_presentation(force=True)

    def clear(self):
        if self.map_layer is not None:
            try:
                self.map.remove_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass
            # self._initialize_layer()

    def remove(self):
        self._removed = True
        self.clear()

    def redraw(self):
        pass

    def update(self):
        # This gets called when subsets are added/updated...
        # which is mostly fine, but
        # a) leaving a tool active means that update gets called
        # b) We need to actually save everything to state
        # print("calling update...")

        if (
            self.map is None
            or self.state.layer is None
            or self._viewer_state.lat_att is None
            or self._viewer_state.lon_att is None
        ):
            return

        self._markers = []
        if self.map_layer.layers is not None:
            self.map_layer.layers = self._markers

        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """
        We need to add a new boolean mode --
            heatmap: which is the default for large? datasets but does not have a lot of options
            layer_group of circle markers: which can do all the cmap and size stuff

        """
        # print(f"Updating layer_artist for points in {self.layer.label} with {force=}")

        if self._removed:
            return

        changed = set() if force else self.pop_changed_properties()
        # print(f"These variables have changed: {changed}")

        # print(f"{self.state.color=}")

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            self.clear()

        # my_logger.debug(f"updating Map for points in {self.layer.label} with {force=}")

        if "display_mode" in changed:
            # print("Updating display_mode")
            if self.state.display_mode == "Individual Points":
                try:
                    self.map.remove_layer(self.map_layer)
                    self.map_layer = LayerGroup(layers=self._markers)
                    self.map.add_layer(self.map_layer)
                except ipyleaflet.LayerException:
                    pass
            else:
                self.map.remove_layer(self.map_layer)
                self.map_layer = Heatmap(
                    locations=self._coords
                )  # This is not quite right
                # because we don't have state objects that describe all these other things that go into a Heatmap
                self.map.add_layer(self.map_layer)

        if self.visible is False:
            self.clear()
        else:
            try:
                self.map.add_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass

        if force or any(x in changed for x in ["lon_att", "lat_att", "display_mode"]):
            # print("Inside lat/lon if statement")
            try:
                lon = self.layer[self._viewer_state.lon_att]
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lon_att)
                return
            # print("Found a good lon")
            try:
                lat = self.layer[self._viewer_state.lat_att]
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lat_att)
                return

            if not len(lon):
                return

            locs = list(zip(lat, lon))
            self._coords = locs
            if self.state.display_mode == "Individual Points":
                try:
                    self._markers = []
                except:  # noqa 722
                    pass
                for lat, lon in self._coords:
                    self._markers.append(
                        CircleMarker(
                            location=(lat, lon),
                            stroke=True,
                            color=color2hex(self.state.color),
                            #fill_color=color2hex(self.state.color),
                            opacity=self.state.alpha,
                            fill_opacity=0,
                            weight=2,
                        )
                    )  # Might want to make this an option.
                    # This is not quite right, we should store the current colors in a state var?
                    # Otherwise, we do not get the colormap value back when toggling display_mode...
                self.map_layer.layers = self._markers  # layers is the attribute here
            else:
                self.map_layer.locations = self._coords

        if force or any(
            x in changed
            for x in [
                "color",
                "color_mode",
                "cmap_att",
                "display_mode",
                "cmap_vmin",
                "cmap_vmax",
                "cmap",
            ]
        ):
            # print("Updating color")
            if self.state.display_mode == "Individual Points":
                if (
                    self.state.color_mode == "Linear"
                    and self.state.cmap_att is not None
                ):
                    try:
                        color_values = (
                            ensure_numerical(self.layer[self.state.cmap_att])
                            .astype(np.float32)
                            .ravel()
                        )
                    except IncompatibleAttribute:
                        self.disable_invalid_attributes(self.state.cmap_att)
                        return
                    #print("Calculating colors...")

                    if "cmap_vmin" not in changed and "cmap_att" in changed:
                        self.state.cmap_vmin = min(color_values)
                    if "cmap_vmax" not in changed and "cmap_att" in changed:
                        self.state.cmap_vmax = max(color_values)
                    diff = (
                        self.state.cmap_vmax - self.state.cmap_vmin or 1
                    )  # to avoid div by zero
                    normalized_vals = (color_values - self.state.cmap_vmin) / diff
                    for marker, val in zip(self._markers, normalized_vals):
                        marker.color = color2hex(self.state.cmap(val))
                else:
                    for marker in self._markers:
                        marker.color = color2hex(self.state.color)

            else:
                try:
                    self.map.remove_layer(self.map_layer)
                    color = color2hex(self.state.color)
                    self.map_layer.gradient = {0: color, 1: color}
                    self.map.add_layer(self.map_layer)
                except ipyleaflet.LayerException:
                    pass

        if force or any(
            x in changed
            for x in [
                "size",
                "size_mode",
                "size_scaling",
                "size_att",
                "display_mode",
                "size_vmin",
                "size_vmax",
            ]
        ):
            # print("Updating size")
            if self.state.size_mode == "Linear" and self.state.size_att is not None:
                # print("Linear mode is active")
                try:
                    size_values = (
                        ensure_numerical(self.layer[self.state.size_att])
                        .astype(np.float32)
                        .ravel()
                    )
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.size_att)
                    return

                if self.state.display_mode == "Individual Points":
                    #print("Calculating sizes")
                    #print(f"{size_values[0:4]=}")
                    if "size_vmin" not in changed and "size_att" in changed:
                        self.state.size_vmin = min(
                            size_values
                        )  # Actually we only want to update this if we swap size_att
                    if "size_vmax" not in changed and "size_att" in changed:
                        self.state.size_vmax = max(size_values)
                    diff = self.state.size_vmax - self.state.size_vmin
                    normalized_vals = (size_values - self.state.size_vmin) / diff
                    # print(f'{self._markers=}')
                    # self.map.remove_layer(self.map_layer)
                    for marker, val in zip(self._markers, normalized_vals):
                        marker.radius = int(
                            (val + 1) * self.state.size_scaling * 5
                        )  # So we always show the points
                        # print(int(val)+1)
                # self.map.add_layer(self.map_layer)

            else:
                size_values = None
                if self.state.display_mode == "Individual Points":
                    for marker in self._markers:
                        marker.radius = self.state.size * self.state.size_scaling
                else:
                    try:
                        self.map.remove_layer(self.map_layer)
                        self.map_layer.radius = (
                            self.state.size * self.state.size_scaling
                        )
                        self.map_layer.blur = self.map_layer.radius / 10
                        self.map.add_layer(self.map_layer)
                    except ipyleaflet.LayerException:
                        pass

        if force or "alpha" in changed:
            if self.state.display_mode == "Individual Points":
                for marker in self._markers:
                    marker.fill_opacity = 0
                    marker.opacity = self.state.alpha
            else:
                try:
                    self.map.remove_layer(self.map_layer)
                    self.map_layer.min_opacity = (
                        self.state.alpha
                    )  # This is not quite right, but close enough
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

    # We probably have to (if possible) make this actually blank
    _fake_geo_json = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "DE",
                "properties": {"name": "Delaware"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.414089, 39.804456],
                            [-75.507197, 39.683964],
                            [-75.414089, 39.804456],
                        ]
                    ],
                },
            }
        ],
    }

    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        # my_logger.warning(f"Calling _init_...")

        super(MapRegionLayerArtist, self).__init__(
            viewer_state, layer_state=layer_state, layer=layer
        )
        self.map_layer = None
        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible
        self.border_weight = 1.0  # This could be user-adjustable

        self._regions = self._fake_geo_json

        if self.state.fill is not None:
            if self.state.fill is False:
                self.fillOpacity = 0
            else:
                self.fillOpacity = self.state.alpha
        else:
            self.fillOpacity = 0
            #self.fillOpacity = self.state.alpha

        self.map_layer = GeoJSON(
            data=self._regions,
            style={
                "fillColor": self.state.color,
                "fillOpacity": self.fillOpacity,
                "opacity": self.state.alpha,
                "color": self.state.color,
                "weight": self.border_weight,
            },
            hover_style={
                "fillOpacity": self.fillOpacity + 0.2,
                "opacity": self.state.alpha + 0.2,
            },
        )
        link((self.state, "visible"), (self.map_layer, "visible"))

        self.state.add_global_callback(self._update_presentation)
        self._viewer_state.add_global_callback(self._update_presentation)

    def clear(self):
        if self.map_layer is not None:
            try:
                self.map.remove_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass
            # self._initialize_layer()

    def remove(self):
        self._removed = True
        self.clear()

    def redraw(self):
        pass

    def update(self):
        if (
            self.map is None
            or self.state.layer is None
            or self._viewer_state.lat_att is None
            or self._viewer_state.lon_att is None
        ):
            return
        # my_logger.warning(f"*** MapRegionLayerArtist.update ***")

        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """ """
        
        # my_logger.warning(f"*** MapRegionLayerArtist._update_presentation ***")

        # my_logger.warning(f"updating Map for regions in {self.layer.label} with {force=}")

        if self._removed:
            return

        changed = set() if force else self.pop_changed_properties()
        # my_logger.warning(f"These variables have changed: {changed}")
        #print(f"{changed=}")
        if (
            not changed and not force
        ):  # or len(changed) > 6: #For some reason the first time we change anything, everything get changed.
            # This is a hack around it.
            return  # Bail quickly

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            self.clear()

        if self.visible is False:
            self.clear()
        else:
            try:
                self.map.add_layer(self.map_layer)
            except ipyleaflet.LayerException:
                pass

        if force or any(x in changed for x in ["lon_att", "lat_att"]):
            # We try to get lat and lon attributes because even though
            # we do not need them for display, we want to ensure
            # that the attributes are linked with other layers
            # print("Inside lat/lon if statement")
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

            if not (len(lon) and len(lat)):
                return
            # my_logger.warning(f"Updating map_layer.data with regions...")

            gdf = GeoPandasTranslator().to_object(self.layer)
            self._regions = json.loads(gdf.to_json())
            self.map_layer.data = self._regions


        if force or any(
            x in changed
            for x in [
                "cmap_att",
                "color_mode",
                "cmap",
                "cmap_vmin",
                "cmap_vmax",
                "color",
            ]
        ):
            if (
                self.state.color_mode == "Linear"
                and self.state.cmap_att is not None
                and self.state.cmap is not None
            ):
                try:
                    cmap_values = (
                        ensure_numerical(self.layer[self.state.cmap_att])
                        .astype(np.float32)
                        .ravel()
                    )
                except IncompatibleAttribute:
                    self.disable_invalid_attributes(self.state.cmap_att)
                    return
                if "cmap_vmin" not in changed and "cmap_att" in changed:
                    self.state.cmap_vmin = min(
                        cmap_values
                    )  # We only want to update this if we swap cmap_att, otherwise allow vmin and vmax to change
                if "cmap_vmax" not in changed and "cmap_att" in changed:
                    self.state.cmap_vmax = max(cmap_values)
                diff = self.state.cmap_vmax - self.state.cmap_vmin
                normalized_vals = (cmap_values - self.state.cmap_vmin) / diff
                mapping = dict(
                    zip(
                        [str(x) for x in self.layer["Pixel Axis 0 [x]"]],
                        normalized_vals,
                    )
                )

                def feature_color(feature):
                    feature_name = feature["id"]
                    region_color = color2hex(self.state.cmap(mapping[feature_name]))
                    return {
                        "fillColor": region_color,
                        "color": region_color,
                        "weight": self.border_weight,
                    }

                # This logic does not seem to work when we change the color first and then go back to linear?
                old_style = self.map_layer.style
                if "color" in old_style:
                    del old_style["color"]
                if "fillColor" in old_style:
                    del old_style["fillColor"]

                # my_logger.warning(f"Setting color for Linear color...")

                self.map_layer.style = old_style
                # We need to blank these https://github.com/jupyter-widgets/ipyleaflet/issues/675#issuecomment-710970550
                self.map_layer.style_callback = feature_color

            elif self.state.color_mode == "Fixed" and self.state.color is not None:
                # my_logger.warning(f"Setting color for Fixed color...")
                self.map_layer.style = {
                    "color": self.state.color,
                    "fillColor": self.state.color,
                    "weight": self.border_weight,
                }
        # if force or 'color' in changed:
        #    if self.state.color is not None and self.state.color_mode == 'Fixed':
        #        self.map_layer.style = {'color':self.state.color, 'fillColor':self.state.color}

        if force or ("alpha" in changed) or ("fill" in changed):
            #if self.state.fill is not None:
            if self.state.fill is False:
                self.fillOpacity = 0
            else:
                self.fillOpacity = self.state.alpha
            #else:
                #self.fillOpacity = self.state.alpha

            if self.state.alpha is not None:
                self.map_layer.style = {
                    "fillOpacity": self.fillOpacity,
                    "opacity": self.state.alpha,
                }
                self.map_layer.hover_style = {
                    "fillOpacity": self.fillOpacity + 0.2,
                    "opacity": self.state.alpha + 0.2,
                }

        self.enable()


class MapXarrayLayerArtist(LayerArtist):
    """
    Display a regularly gridded Xarray dataset on the map as an ImageOverlay
    """
    _layer_state_cls = MapXarrayLayerState
    _removed = False

    def __init__(self, viewer_state, map=None, layer_state=None, layer=None):
        super().__init__(
            viewer_state, layer_state=layer_state, layer=layer
        )

        self.layer = layer
        self.layer_id = "{0:08x}".format(random.getrandbits(32))
        self.map = map
        self.zorder = self.state.zorder
        self.visible = self.state.visible
        self.image_overlay_layer = ImageOverlay()
        self.vmin = 0
        self.vmax = 1
        self.map.add(self.image_overlay_layer)
        self.bounds = [(0, 0), (0, 0)]
        if isinstance(self.layer, Data):
            self._sliced_data = IndexedData(self.layer, indices=(self.state.t, None, None))
        else:
            self._sliced_data = None
        self.state.add_global_callback(self.update)

        #  In theory we want something like this to link the opacity of the layer to the alpha of the state
        #  dlink((self.state, 'alpha'), (self.image_overlay_layer, 'opacity'), lambda x: [x])

    def remove(self):
        self._removed = True
        self.clear()

    def redraw(self):
        pass

    def update(self, **kwargs):
        if (
            self.map is None
            or self.state.layer is None
            or self._viewer_state.lat_att is None
            or self._viewer_state.lon_att is None
        ):
            return
        self._update_presentation(force=True)

    def _update_presentation(self, force=False, **kwargs):
        """ """
        #print(f"Entering _update_presentation with {force=} at time {time()}")

        if self._removed:
            return

        changed = set() if force else self.pop_changed_properties()
        #print(f"_update_presentation has {changed=} at time {time()}")

        #print(changed)
        if (not changed and not force) or len(changed) > 6: 
            return  # Bail quickly

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None or self.state.data_att is None:
            self.clear()
            return

        #if self.visible is False:
        #    self.clear()

        if force or any(x in changed for x in ["data_att"]):
            self.vmin = 0#self.layer.compute_statistic('percentile', self.state.data_att, percentile=1, random_subset=10000)
            self.vmax = 1#self.layer.compute_statistic('percentile', self.state.data_att, percentile=99, random_subset=10000)


        #print(f"Preliminaries done at time {time()}")
        if not isinstance(self.layer, Data): # Bail on subsets for now
            return
        if force or any(x in changed for x in ["lon_att", "lat_att", "data_att"]):
            try:
                lon = self._sliced_data.get_data(self._viewer_state.lon_att)
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lon_att)
                return

            try:
                lat = self._sliced_data.get_data(self._viewer_state.lat_att)
            except IncompatibleAttribute:
                self.disable_invalid_attributes(self._viewer_state.lat_att)
                return

            if not (len(lon) and len(lat)):
                return
            #print(f"Lat/lon grabbed at time {time()}")

            if isinstance(self.layer, Data):

                self.bounds = [(lat.min(), lon.min()), (lat.max(), lon.max())]
                #print(f"Bounds ({self.bounds=}) calculated time {time()}")

                def normalize_over_full_data(array, *args, **kwargs):
                    array = (array - self.vmin) / (self.vmax - self.vmin)
                    return array
                self.norm_func = normalize_over_full_data


        if force or any(x in changed for x in ["lon_att", "lat_att", "t", "cmap"]):
            if isinstance(self.layer, Data):
                self._sliced_data.indices = (self.state.t, None, None)
            # Check if this is a data or a subset layer
                data = self._sliced_data.get_data(self.state.data_att)
                #print(f"data loaded {time()}")
                #print(f"Data shape: {data.shape}")
                #print(f"{self.state.cmap=}")
                imgurl = make_imageoverlay(data, self.bounds, self.norm_func,
                                            proj_refinement=1, colormap=self.state.cmap)
                #print(f"imgrul made {time()}")

                self.image_overlay_layer.url = imgurl
                self.image_overlay_layer.bounds = self.bounds
                #print(f"layer updated {time()}")
            else:
                pass

        #if force or "visible" in changed:
        self.image_overlay_layer.visible = self.state.visible

        #self.enable()





def project_array(array, bounds, refinement=2):
    """
    Project a numpy array defined in WGS84 coordinates to Mercator Web coordinate system
    
    ipyleaflets use the Mercator Web coordinate system.
    :arg array: Data in 2D numpy array
    :arg bounds: Image latitude, longitude bounds, [(lat_min, lon_min), (lat_max, lon_max)]
    :kwarg int refinement: Scaling factor for output array resolution.
        refinement=1 implies that output array has the same size as the input.
    """
    with rasterio.Env():

        (lat_min, lon_min), (lat_max, lon_max) = bounds
        nlat, nlon = array.shape
        dlat = (lat_max - lat_min)/nlat
        dlon = (lon_max - lon_min)/nlon
        src_transform = A.translation(lon_min, lat_min) * A.scale(dlon, dlat)
        src_crs = {'init': 'EPSG:4326'}

        nlat2 = nlat*refinement
        nlon2 = nlon*refinement
        dst_shape = (nlat2, nlon2)
        dst_crs = {'init': 'EPSG:3857'}
        bbox = [lon_min, lat_min, lon_max, lat_max]
        dst_transform, width, height = rasterio.warp.calculate_default_transform(
            src_crs, dst_crs, nlon, nlat, *bbox, dst_width=nlon2, dst_height=nlat2)
        dst_shape = height, width
        destination = np.zeros(dst_shape)

        reproject(
            array,
            destination,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
        return destination


def make_imageoverlay(array, bounds, norm_func, mask=None, colormap='Blues', proj_refinement=4):
    """
    Make ImageOverlay from numpy array.
    
    
    :arg array: Data in 2D numpy array.
    :arg bounds: Image latitude, longitude bounds, [(lat_min, lon_min), (lat_max, lon_max)]
    :kwarg mask: Optional mask to mark missing data in the array. If mask=None and array is
        a masked array, its mask is used instead.
    :kwarg colormap: matplotlib colormap
    :kwarg int refinement: Scaling factor for output array resolution.
        refinement=1 implies that output array has the same size as the input.
    """
    if mask is None and hasattr(array, 'mask'):
        mask = array.mask
    # project to Mercator Web coordinates
    array_proj = project_array(array, bounds, refinement=proj_refinement)
    cmap = plt.get_cmap(colormap)
    array_mapped = cmap(norm_func(array_proj))
    # convert to 8 bit int
    array_int = np.uint8(array_mapped*255)
    # make an image
    im = PIL.Image.new('RGBA', array_proj.shape[::-1], color=None)
    im_data = PIL.Image.fromarray(array_int)
    im_mask = None
    if mask is not None:
        assert mask.shape == array.shape, 'array and mask shapes must be identical'
        mask = project_array(mask.astype(float), bounds, refinement=proj_refinement)
        # NOTE image mask marks non-masked pixels
        mask_int = np.uint8(255*(1 - mask).astype(float))
        im_mask = PIL.Image.fromarray(mask_int, mode='L')
    im.paste(im_data, mask=im_mask)
    # store image in memory
    f = BytesIO()
    im.save(f, 'png')
    data = b64encode(f.getvalue())
    data = data.decode('ascii')
    imgurl = 'data:image/png;base64,' + data
    return imgurl