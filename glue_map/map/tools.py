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
            # print("On click called...")
            self.list_of_region_ids = []
            # print(f"{feature=}")
            feature_id = feature["id"]  # This is the name of features in our geodata
            # List of region_ids should start with the current subset (how to get this?)
            #active_subset = self.viewer.toolbar_active_subset.selected
            #self.list_of_region_ids.append(int(feature_id))
            #self.list_of_region_ids = list(set(self.list_of_region_ids))
            # print(f"List of region ids to draw... {self.list_of_region_ids}")
            # In this case we are creating CategorySubsetStates
            # from the names of the selected regions. This is very
            # specific to the TEMPO data.

            # To make it not hard-coded we would need an attribute
            # in the mapviewer that was the select_att
            category_name = self.viewer.state.select_att.label
            region_name = feature["properties"][category_name]
            roi = CategoricalROI([region_name, category_name])
            new_subset_state = CategoricalROISubsetState(att=self.viewer.state.select_att, roi=roi)

            # This is the standard way to add a subset -- it enables
            # undo, and deals with the subset_mode thing correctly, 
            # but it does not allow us to set the label. Ultimately
            # we probably want to use this and then figure out a way to set the
            # labels afterwards. Boolean logic on subsets make naming a subset
            # complicated anyway.

            self.viewer.apply_subset_state(new_subset_state, override_mode=None)

            # This is the manual way to set up a new subset group, and the only real problem
            # is that it does not adjust the subset_mode
            #self.viewer.session.data_collection.new_subset_group(region_name, new_subset_state)
            #from glue.core.edit_subset_mode import ReplaceMode
            ## Switch subset_mode to show the new subset
            #self.viewer.session.edit_subset_mode = ReplaceMode#self.viewer.session.data_collection.subset_groups[-1]

            #self.viewer.session.edit_subset_mode._edit_mode = self.viewer.session.data_collection.subset_groups[-1]


            # Now this renaming happens AFTER the subset is added to all the other viewers
            # That's mostly fine, as it should (I think) trigger a subset_changed message
            for subset_group in self.viewer.session.data_collection.subset_groups:
                # The memory address of the SubsetState is not preserved by
                # apply_subset_state, so we compare the ROI in order to apply
                # the nice label to the subset group.
                #print(f"{subset_group.subset_state.roi.categories=}")
                #print(f"{new_subset_state.roi.categories=}")
                #print(f"{subset_group.subset_state.att=}")
                #print(f"{new_subset_state.att=}")

                if np.array_equal(subset_group.subset_state.roi.categories, new_subset_state.roi.categories):
                    subset_group.label = region_name
                    subset_group.style.alpha = 0.9

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

    def activate(self):
        """ """
        self.viewer.map.dragging = False

        def map_interaction(**kwargs):
            # print(kwargs)
            if kwargs["type"] == "mousedown":
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

                self.start_coords = None
                time.sleep(0.1)
                self.viewer.map.remove_layer(self.rect)
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
