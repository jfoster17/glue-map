import os

import numpy as np
from glue.config import viewer_tool
from glue.core.roi import PolygonalROI, RectangularROI
from glue.core.subset import MultiOrState, RoiSubsetState
from glue.viewers.common.tool import CheckableTool, Tool
from ipyleaflet import Rectangle, Polygon, Polyline, LayerException
from ipywidgets import CallbackDispatcher

__all__ = []

ICON_WIDTH = 20
INTERACT_COLOR = "yellow"

ICONS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'icons')


class InteractCheckableTool(CheckableTool):
    def __init__(self, viewer):
        self.viewer = viewer

    def activate(self):
        # Disable any active tool in other viewers
        for viewer in self.viewer.session.application.viewers:
            if viewer is not self.viewer:
                viewer.toolbar.active_tool = None

        self.viewer._mouse_interact.next = self.interact

    #def deactivate(self):
    #    self.viewer._mouse_interact.next = None


class IpyLeafletSelectionTool(InteractCheckableTool):
    def activate(self):
        # Jumps back to "create new" if that setting is active
        if self.viewer.session.application.get_setting(
            "new_subset_on_selection_tool_change"
        ):
            self.viewer.session.edit_subset_mode.edit_subset = None
        super().activate()


@viewer_tool
class PointSelect(IpyLeafletSelectionTool):
    icon = "glue_crosshair"
    tool_id = "ipyleaflet:pointselect"
    action_text = "Select regions"
    tool_tip = "Select regions"
    status_tip = "Click to create subsets from regions"
    shortcut = "D"

    def __init__(self, viewer):
        super(PointSelect, self).__init__(viewer)
        #self.list_of_region_ids = []
        # print("PointSelect created...")

    def activate(self):
        """
        Capture point-select clicks. This is to select regions...
        """
        #print("PointSelect activated...")

        def on_click(event, feature, **kwargs):
            feature_id = feature["id"]  # This is the name of features in our geodata

            try:
                coord = feature["geometry"]["coordinates"]
                new_subset_states = []
                # Loop through MultiPolygon types
                for region in coord:
                    lons = []
                    lats = []
                    for k in np.squeeze(region):
                        lons.append(k[0])
                        lats.append(k[1])
                    roi = PolygonalROI(vx=lons, vy=lats)
                    new_subset_state = RoiSubsetState(
                        xatt=self.viewer.state.lon_att,
                        yatt=self.viewer.state.lat_att,
                        roi=roi,
                    )
                    new_subset_states.append(new_subset_state)
                if len(new_subset_states) == 1:
                    final_subset_state = new_subset_states[0]
                else:
                    final_subset_state = MultiOrState(new_subset_states)
                self.viewer.apply_subset_state(final_subset_state, override_mode=None)

            except OSError:
                print("Feature has no geometry defined...")
                pass

        for map_layer in self.viewer.map.layers:
            # Perhaps (perhaps not) make this limited to RegionLayerArtists?
            map_layer.on_click(on_click)

    def deactivate(self):
        for map_layer in self.viewer.map.layers:
            map_layer._click_callbacks = (
                CallbackDispatcher()
            )  # This removes all on_click callbacks, but seems to work
            self.list_of_region_ids = (
                []
            )  # We need to trigger this when we switch modes too (to do a new region)

    def close(self):
        pass


@viewer_tool
class LassoSelect(IpyLeafletSelectionTool):
    icon = os.path.join(ICONS_DIR, "glue_lasso")
    tool_id = "ipyleaflet:lassoselect"
    action_text = "Lasso"
    tool_tip = "Lasso a region of interest"
    status_tip = "Lasso a region of interest"

    def __init__(self, viewer):
        super(LassoSelect, self).__init__(viewer)
        # create an empty two dimensional array to store the points
        self.points = []
        self.show_subset = False
        self.poly = None
        self.patch_x = []
        self.patch_y = []
        self.styling = {"color": INTERACT_COLOR,
                        "fill_color": INTERACT_COLOR,
                        "weight": 1,
                        "fill_opacity": 0.5,
                        "dash_array": "5, 5"}

    def activate(self):
        self.viewer.map.dragging = False
        self.show_subset = False
        self.start_coords = None
        self.points = []
        self.poly = Polygon(locations=[], **self.styling)
        self.patch_x = []
        self.patch_y = []

        def map_interaction(**kwargs):
            
            # Start a new region on mousedown
            if kwargs["type"] == "mousedown":
                if self.show_subset:
                    try:
                        self.viewer.map.remove_layer(self.poly)
                        self.show_subset = False
                    except LayerException:
                        pass
                x, y = kwargs["coordinates"]
                self.start_coords = kwargs["coordinates"]
                self.points.append(kwargs["coordinates"])
                self.patch_x.append(x)
                self.patch_y.append(y)
                self.poly.locations = self.points
                self.viewer.map.add_layer(self.poly)

            elif kwargs["type"] == "mousemove" and self.start_coords:
                self.points.append(kwargs["coordinates"])
                x, y = kwargs["coordinates"]
                self.patch_x.append(x)
                self.patch_y.append(y)
                new_poly = Polygon(locations=self.points, **self.styling)
                self.viewer.map.substitute_layer(self.poly, new_poly)
                self.poly = new_poly
            elif kwargs["type"] == "mouseup" and self.start_coords:
                self.close_vertices()
            elif kwargs["type"] == "mouseleave" and self.start_coords:
                self.close_vertices()
        self.viewer.map.on_interaction(map_interaction)

    def close_vertices(self):
        roi = PolygonalROI(vx=self.patch_y, vy=self.patch_x)
        self.viewer.apply_roi(roi)
        self.show_subset = True
        try:
            self.viewer.map.remove_layer(self.poly)
        except LayerException:
            pass
        self.deactivate(no_close=True)

    def deactivate(self, no_close=False):
        if len(self.points) > 1 and not no_close:
            self.close_vertices()
        self.viewer.map.dragging = True
        self.viewer.map._interaction_callbacks = CallbackDispatcher()
        self.start_coords = None
        self.points = []
        self.poly = Polygon(locations=[], **self.styling)
        self.patch_x = []
        self.patch_y = []

    def close(self):
        pass


@viewer_tool
class PolygonSelect(IpyLeafletSelectionTool):
    icon = os.path.join(ICONS_DIR, "glue_polygon")
    tool_id = "ipyleaflet:polygonselect"
    action_text = "Polygonal ROI"
    tool_tip = "Click to define polygonal region of interest"
    status_tip = "Draw a polygonal region of interest"

    def __init__(self, viewer):
        super(PolygonSelect, self).__init__(viewer)
        # create an empty two dimensional array to store the points
        self.points = []
        self.show_subset = False
        self.poly = None
        self.patch_x = []
        self.patch_y = []
        self.styling = {"color": INTERACT_COLOR,
                        "fill_color": INTERACT_COLOR,
                        "weight": 1,
                        "fill_opacity": 0.5,
                        "dash_array": "5, 5"}
    
    def activate(self):
        self.viewer.map.dragging = False
        self.show_subset = False

        self.points = []
        self.poly = Polygon(locations=[], **self.styling)
        self.patch_x = []
        self.patch_y = []

        def map_interaction(**kwargs):
            if kwargs["type"] == "click":
                if self.show_subset:
                    try:
                        self.viewer.map.remove_layer(self.poly)
                        self.show_subset = False
                    except LayerException:
                        pass
                x, y = kwargs["coordinates"]
                #print(f"Click at {x}, {y}")
                if len(self.points) == 0:
                    self.points.append(kwargs["coordinates"])
                    self.patch_x.append(x)
                    self.patch_y.append(y)
                    self.poly.locations = self.points
                    #print(f"Adding layer with {self.points}")
                    self.viewer.map.add_layer(self.poly)
                elif len(self.points) > 0:
                    #print("More than one point...")
                    #print(f"{self.points=}")
                    #print(f"{self.poly.locations=}")
                    sz = max(self.patch_x) - min(self.patch_x), max(self.patch_y) - min(self.patch_y)
                    if (abs(x - self.patch_x[0]) < 0.02 * sz[0] and abs(y - self.patch_y[0]) < 0.02 * sz[1]):
                        self.close_vertices()
                    else:
                        # We double-track the set of coordinates
                        # just to make the calculation easier
                        self.points.append(kwargs["coordinates"])
                        self.patch_x.append(x)
                        self.patch_y.append(y)
                        if len(self.points) == 2:
                            new_poly = Polyline(locations=self.points, **self.styling)
                        else:
                            new_poly = Polygon(locations=self.points, **self.styling)
                        self.viewer.map.substitute_layer(self.poly, new_poly)
                        self.poly = new_poly
                        # In theory we could just update the locations
                        # but this does not seem to work consistently.
                        #self.poly.locations = self.points

        self.viewer.map.on_interaction(map_interaction)

    def close_vertices(self):
        #print("Closing vertices...")
        roi = PolygonalROI(vx=self.patch_y, vy=self.patch_x)
        #print(f"{roi=}")
        self.viewer.apply_roi(roi)

        self.show_subset = True
        try:
            self.viewer.map.remove_layer(self.poly)
        except LayerException:
            pass

    def deactivate(self):
        if len(self.points) > 1:
            self.close_vertices()
        self.viewer.map.dragging = True
        self.viewer.map._interaction_callbacks = CallbackDispatcher()
        super().deactivate()

    def close(self):
        pass



@viewer_tool
class RectangleSelect(IpyLeafletSelectionTool):
    icon = "glue_square"
    tool_id = "ipyleaflet:rectangleselect"
    action_text = "Rectangular ROI"
    tool_tip = "Drag to define a rectangular region of interest"
    status_tip = "Define a rectangular region of interest"
    shortcut = "D"

    def __init__(self, viewer):
        super(RectangleSelect, self).__init__(viewer)
        self.start_coords = None
        self.end_coords = None
        self.show_subset = False

    def activate(self):
        """ """
        self.viewer.map.dragging = False

        def map_interaction(**kwargs):
            # print(kwargs)
            if kwargs["type"] == "mousedown":
                if self.show_subset:
                    try:
                        self.viewer.map.remove_layer(self.rect)
                        self.show_subset = False
                    except LayerException:
                        pass
                #print(f'mousedown {kwargs["coordinates"]}')
                self.start_coords = kwargs["coordinates"]
                self.rect = Rectangle(
                    bounds=(self.start_coords, kwargs["coordinates"]),
                    weight=1,
                    fill_opacity=0,
                    dash_array="5, 5",
                    color=INTERACT_COLOR,
                )
                self.viewer.map.add_layer(self.rect)
            elif kwargs["type"] == "mouseup" and self.start_coords:
                #print(f'mouseup {kwargs["coordinates"]}')
                self.end_coords = kwargs["coordinates"]

                xmin = self.end_coords[1]
                xmax = self.start_coords[1]
                ymin = self.end_coords[0]
                ymax = self.start_coords[0]
                xmin, xmax = sorted((xmin, xmax))
                ymin, ymax = sorted((ymin, ymax))
                #print(f"{xmin=}, {xmax=}, {ymin=}, {ymax=}")
                roi = RectangularROI(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)
                #roi = Polygonal
                #print("Applying ROI...")
                self.viewer.apply_roi(roi)

                #time.sleep(0.1)

                new_rect = Rectangle(
                    bounds=(self.start_coords, self.end_coords),
                    weight=1,
                    fill_opacity=0.5,
                    dash_array="5, 5",
                    color=INTERACT_COLOR,
                    fill_color=INTERACT_COLOR,
                )
                self.start_coords = None

                self.viewer.map.substitute_layer(self.rect, new_rect)
                self.show_subset = True
                self.rect = new_rect
                #self.rect.color = "purple"
                self.viewer.map.remove_layer(self.rect)
                self.end_coords = None
            elif kwargs["type"] == "mousemove" and self.start_coords:
                new_rect = Rectangle(
                    bounds=(self.start_coords, kwargs["coordinates"]),
                    weight=1,
                    fill_opacity=0.1,
                    dash_array="5, 5",
                    color="yellow",
                    fill_color="yellow",
                )

                self.viewer.map.substitute_layer(self.rect, new_rect)
                self.rect = new_rect

        self.viewer.map.on_interaction(map_interaction)

    def deactivate(self):
        self.viewer.map.dragging = True
        self.viewer.map._interaction_callbacks = CallbackDispatcher()
        # self.viewer.mapfigure.dragging = True

    def close(self):
        pass


@viewer_tool
class HomeTool(Tool):
    tool_id = "ipyleaflet:home"
    icon = "glue_home"
    action_text = "Home"
    tool_tip = "Reset original zoom"

    def activate(self):
        self.viewer.state.reset_limits()
