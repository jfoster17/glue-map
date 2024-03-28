import os
import time

import numpy as np
from glue.config import viewer_tool
from glue.core.roi import PolygonalROI, RectangularROI, CategoricalROI
from glue.core.subset import MultiOrState, OrState, RoiSubsetState, CategoricalROISubsetState
from glue.viewers.common.tool import CheckableTool, Tool
from ipyleaflet import Rectangle
from ipywidgets import CallbackDispatcher

__all__ = []

ICON_WIDTH = 20
INTERACT_COLOR = "#cbcbcb"

ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "icons")


class InteractCheckableTool(CheckableTool):
    def __init__(self, viewer):
        self.viewer = viewer

    def activate(self):
        # Disable any active tool in other viewers
        for viewer in self.viewer.session.application.viewers:
            if viewer is not self.viewer:
                viewer.toolbar.active_tool = None

        self.viewer._mouse_interact.next = self.interact

    def deactivate(self):
        self.viewer._mouse_interact.next = None


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
                    self.viewer.map.remove_layer(self.rect)
                    self.show_subset = False
                #print(f'mousedown {kwargs["coordinates"]}')
                self.start_coords = kwargs["coordinates"]
                self.rect = Rectangle(
                    bounds=(self.start_coords, kwargs["coordinates"]),
                    weight=1,
                    fill_opacity=0,
                    dash_array="5, 5",
                    color="gray",
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
                #print("Applying ROI...")
                self.viewer.apply_roi(roi)

                #time.sleep(0.1)

                new_rect = Rectangle(
                    bounds=(self.start_coords, self.end_coords),
                    weight=1,
                    fill_opacity=0.5,
                    dash_array="5, 5",
                    color="purple",
                    fill_color="purple",
                )
                self.start_coords = None

                self.viewer.map.substitute_layer(self.rect, new_rect)
                self.show_subset = True
                self.rect = new_rect
                #self.rect.color = "purple"
                #self.viewer.map.remove_layer(self.rect)
                self.end_coords = None
            elif kwargs["type"] == "mousemove" and self.start_coords:
                new_rect = Rectangle(
                    bounds=(self.start_coords, kwargs["coordinates"]),
                    weight=1,
                    fill_opacity=0.1,
                    dash_array="5, 5",
                    color="gray",
                    fill_color="gray",
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
