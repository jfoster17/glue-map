import ipyleaflet
import ipywidgets
from glue.core.subset import roi_to_subset_state

# from glue.logger import logger
from glue.utils import color2hex
from glue_jupyter.link import dlink, link
from glue_jupyter.utils import float_or_none
from glue_jupyter.view import IPyWidgetView
from glue_jupyter.widgets import Color, Size
from ipywidgets import VBox

from .layer_artist import (MapPointsLayerArtist, MapRegionLayerArtist,
                           MapXarrayLayerArtist, MapImageServerLayerArtist,
                           MapImageServerSubsetLayerArtist)
from .state import MapViewerState
from .state_widgets.viewer_map import MapViewerStateWidget
from .state_widgets.layer_map import MapLayerStateWidget
from .utils import get_geom_type
from ..data import RemoteGeoData_ArcGISImageServer

__all__ = ["IPyLeafletMapViewer"]


class SimpleColor(VBox):
    def __init__(self, state, **kwargs):
        super(SimpleColor, self).__init__(**kwargs)
        self.state = state
        self.widget_color = ipywidgets.ColorPicker(description="color")
        link((self.state, "color"), (self.widget_color, "value"), color2hex)
        self.children = (self.widget_color,)


class SimpleSize(VBox):
    def __init__(self, state, **kwargs):
        super(SimpleSize, self).__init__(**kwargs)
        self.state = state

        self.widget_size = ipywidgets.FloatSlider(
            description="size", min=0, max=10, value=self.state.size
        )
        link((self.state, "size"), (self.widget_size, "value"))
        self.widget_scaling = ipywidgets.FloatSlider(
            description="scale", min=0, max=2, value=self.state.size_scaling
        )
        link((self.state, "size_scaling"), (self.widget_scaling, "value"))

        self.children = (self.widget_size, self.widget_scaling)


class PointsLayerStateWidget(VBox):
    def __init__(self, layer_state):
        self.state = layer_state

        display_mode_options = type(self.state).display_mode.get_choice_labels(
            self.state
        )
        self.widget_display_mode = ipywidgets.RadioButtons(
            options=display_mode_options, description="display mode"
        )
        link((self.state, "display_mode"), (self.widget_display_mode, "value"))

        self.color_widgets = Color(state=self.state)
        self.size_widgets = Size(state=self.state)

        self.size_widgets.widget_size_vmax.description = "size max"

        # self.simple_color_widgets = SimpleColor(state=self.state)
        self.simple_size_widgets = SimpleSize(state=self.state)

        self.widget_alpha = ipywidgets.FloatSlider(
            description="opacity", min=0, max=1, value=self.state.alpha
        )
        link((self.state, "alpha"), (self.widget_alpha, "value"))

        # Only show full color_widget for Individual Points mode
        dlink(
            (self.widget_display_mode, "value"),
            (self.color_widgets.layout, "display"),
            lambda value: None if value == display_mode_options[1] else "none",
        )
        # Only show full size_widget for Individual Points mode
        dlink(
            (self.widget_display_mode, "value"),
            (self.size_widgets.layout, "display"),
            lambda value: None if value == display_mode_options[1] else "none",
        )

        ## Only show simple color_widget for Individual Points mode
        # dlink((self.widget_display_mode, 'value'), (self.simple_color_widgets.layout, 'display'),
        #    lambda value: None if value == display_mode_options[0] else 'none')

        # Only show simple size_widget for Individual Points mode
        dlink(
            (self.widget_display_mode, "value"),
            (self.simple_size_widgets.layout, "display"),
            lambda value: None if value == display_mode_options[0] else "none",
        )

        super().__init__(
            [
                self.widget_display_mode,
                self.size_widgets,
                self.color_widgets,
                self.simple_size_widgets,
                self.widget_alpha,
            ]
        )


class RegionLayerStateWidget(VBox):
    def __init__(self, layer_state):
        self.state = layer_state
        self.color_widgets = Color(state=self.state)
        self.widget_alpha = ipywidgets.FloatSlider(
            description="opacity", min=0, max=1, value=self.state.alpha
        )
        link((self.state, "alpha"), (self.widget_alpha, "value"))

        super().__init__([self.color_widgets, self.widget_alpha])


class XarrayLayerStateWidget(VBox):
    def __init__(self, layer_state):
        self.state = layer_state
        self.color_widgets = Color(state=self.state)
        self.widget_alpha = ipywidgets.FloatSlider(
            description="opacity", min=0, max=1, value=self.state.alpha
        )
        link((self.state, "alpha"), (self.widget_alpha, "value"))

        super().__init__([self.color_widgets, self.widget_alpha])


class ImageServerLayerStateWidget(VBox):
    def __init__(self, layer_state):
        self.state = layer_state
        #self.color_widgets = Color(state=self.state)
        self.widget_opacity = ipywidgets.FloatSlider(
            description="opacity", min=0, max=1, value=self.state.opacity
        )
        link((self.state, "opacity"), (self.widget_opacity, "value"))

        colorscape_options = ['Viridis', 'Magma', 'Inferno', 'Plasma']
        self.widget_colorscale = ipywidgets.Dropdown(
            options=colorscape_options, description="Colorscape"
        )
        link((self.state, "colorscale"), (self.widget_colorscale, "value"))

        super().__init__([self.widget_opacity, self.widget_colorscale])


class IPyLeafletMapViewer(IPyWidgetView):
    """
    A glue viewer to show an `ipyleaflet` Map viewer with data.

    The data can either be regions (using a MapRegionLayerArtist)
    or point-like data (using a MapPointsLayerArtist)

    """

    LABEL = "Map Viewer (ipleaflet)"
    map = None  # The ipyleaflet Map object

    allow_duplicate_data = True
    allow_duplicate_subset = False

    _state_cls = MapViewerState
    _options_cls = MapViewerStateWidget
    _layer_style_widget_cls = {
        MapRegionLayerArtist: RegionLayerStateWidget,  # Do our own RegionLayerStateWidget
        MapPointsLayerArtist: PointsLayerStateWidget,
        MapXarrayLayerArtist: XarrayLayerStateWidget,
        MapImageServerLayerArtist: ImageServerLayerStateWidget,
        MapImageServerSubsetLayerArtist: ImageServerLayerStateWidget,

    }

    tools = ["ipyleaflet:rectangleselect", 'ipyleaflet:polygonselect', 'ipyleaflet:lassoselect']

    def __init__(self, session, state=None):
        # logger.debug("Creating a new Viewer...")
        super(IPyLeafletMapViewer, self).__init__(session, state=state)

        self._initialize_map()

        link((self.state, "zoom_level"), (self.map, "zoom"), float_or_none)
        link((self.state, "center"), (self.map, "center"))

        self.state.add_global_callback(self._update_map)
        self._update_map(force=True)
        self.create_layout()

    def _initialize_map(self):
        self.map = ipyleaflet.Map(basemap=self.state.basemap, prefer_canvas=True)

    def _update_map(self, force=False, **kwargs):
        if force or "basemap" in kwargs:
            pass  # Change basemap

    def get_layer_artist(self, cls, layer=None, layer_state=None):
        """Need to add a reference to the ipyleaflet Map object"""
        return cls(self.map, self.state, layer=layer, layer_state=layer_state)

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if isinstance(layer, RemoteGeoData_ArcGISImageServer):
            cls = MapImageServerLayerArtist
        elif get_geom_type(layer) == "regions":
            cls = MapRegionLayerArtist
        elif get_geom_type(layer) == "points":
            cls = MapPointsLayerArtist
        elif get_geom_type(layer) == "xarray":
            cls = MapXarrayLayerArtist
        else:
            raise ValueError(
                f"IPyLeafletMapViewer does not know how to render the data in {layer.label}"
            )
        return cls(self.state, map=self.map, layer=layer, layer_state=layer_state)

    def get_subset_layer_artist(self, layer=None, layer_state=None):

        if isinstance(layer.data, RemoteGeoData_ArcGISImageServer):
            cls = MapImageServerSubsetLayerArtist
        else:
            if get_geom_type(layer.data) == "regions":
                cls = MapRegionLayerArtist
            elif get_geom_type(layer.data) == "points":
                cls = MapPointsLayerArtist
            elif get_geom_type(layer.data) == "xarray":
                cls = MapXarrayLayerArtist
            else:
                raise ValueError(
                    f"IPyLeafletMapViewer does not know how to render the data in {layer.label}"
                )
        return cls(self.state, map=self.map, layer=layer, layer_state=layer_state)

    def apply_roi(self, roi, override_mode=None):
        # print("Inside apply_roi")
        self.redraw()

        if len(self.layers) == 0:
            return
        subset_state = roi_to_subset_state(
            roi,
            x_att=self.state.lon_att,
            y_att=self.state.lat_att,
        )
        self.apply_subset_state(subset_state, override_mode=override_mode)

    @property
    def figure_widget(self):
        return self.map

    def redraw(self):
        pass
