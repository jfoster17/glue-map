from glue.core.hub import HubListener

from glue.viewers.scatter.state import ScatterViewerState, ScatterLayerState
from glue.viewers.matplotlib.state import (DeferredDrawSelectionCallbackProperty as DDSCProperty,
                                           DeferredDrawCallbackProperty as DDCProperty)
from glue.core.data_combo_helper import ComponentIDComboHelper
from glue.core import BaseData
from glue.core.data_combo_helper import ManualDataComboHelper
from shapely.geometry import Polygon
import shapely
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from timezonefinder import TimezoneFinder
from glue.core.message import SubsetUpdateMessage

__all__ = ['TracesViewerState', 'TracesLayerState']

tf = TimezoneFinder()

month_to_season_lu = np.array([
    None,
    'Winter', 'Winter',
    'Spring', 'Spring', 'Spring',
    'Summer', 'Summer', 'Summer',
    'Fall', 'Fall', 'Fall',
    'Winter'
])


def weekend_or_holiday(rec):
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start='2023-01-01', end='2030-12-31').to_pydatetime()
    holiday_dates = [x.date() for x in holidays]

    if (rec['Day'] in holiday_dates) or (rec['Day of Week'] > 4):
        return "Weekend_or_Holiday"
    else:
        return "Work Day"


class TracesViewerState(ScatterViewerState):

    reference_data = DDSCProperty(docstring='Reference data')
    group_att = DDSCProperty(docstring='Multiple data-points will be grouped by this attribute before plotting.', default_index=-1)
    #I don't think we need this? In general we want to group over x_att
    #agg_att = DDSCProperty(docstring='Attribute to aggregate over (mean) before plotting')

    estimator = DDCProperty('mean', docstring="Function to use to aggregate data points in each group")
    errorbar = DDCProperty('std', docstring="Whether to show error bars [None, 'std', 'sem', 'pi', 'ci']")

    def __init__(self, **kwargs):
        super().__init__()
        self.x_att_helper = ComponentIDComboHelper(self, 'x_att', categorical=False)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', categorical=False)
        self.group_att_helper = ComponentIDComboHelper(self, 'group_att', categorical=True)
        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')

    def _layers_changed(self, *args):
        super()._layers_changed(*args)
        self.group_att_helper.set_multiple_data(self.layers_data)
        self._update_combo_ref_data()
        self._set_reference_data()

    def _set_reference_data(self):
        if self.reference_data is None:
            for layer in self.layers:
                if isinstance(layer.layer, BaseData):
                    self.reference_data = layer.layer
                    return

    def _update_combo_ref_data(self):
        self.ref_data_helper.set_multiple_data(self.layers_data)


class TracesLayerState(ScatterLayerState, HubListener):

    markers_visible = DDCProperty(False, docstring="Whether to show markers")
    line_visible = DDCProperty(True, docstring="Whether to show a line connecting all positions")

    _layer_subset_updates_subscribed = False
    _profile_cache = None
    
    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state, **kwargs)

    def _on_layer_change(self, *args):

        if self.layer is not None:

            # Set the available attributes
            #self.attribute_att_helper.set_multiple_data([self.layer])

            # We only subscribe to SubsetUpdateMessage the first time that 'layer'
            # is not None, and then do any filtering in the callback function.
            if not self._layer_subset_updates_subscribed and self.layer.hub is not None:
                self.layer.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)
                self._layer_subset_updates_subscribed = True

        self.reset_cache()

    def _on_subset_update(self, msg):
        if msg.subset is self.layer:
            self.reset_cache()

    @property
    def profile(self):
        return self._profile_cache

    def reset_cache(self, *args):
        # If this is a subset for a region that is already cached
        # we simply return the cached profile. Doing this basically
        # ignores all the other options in the profile viewer and
        # just relies on the subset label
        if not isinstance(self.layer, BaseData):
            print("In reset_cache")
            try:
                region_geom = self.layer.subset_state.roi.to_polygon()
            except AttributeError:
                self._profile_cache = None
                return
            clip_poly = Polygon([(x, y) for x, y in zip(region_geom[0], region_geom[1])])
            center = shapely.centroid(clip_poly)
            center_lon, center_lat = center.x, center.y
            print(f"center_lon: {center_lon}, center_lat: {center_lat}")
            tz = tf.timezone_at(lng=center_lon, lat=center_lat)
            region_clip = self.viewer_state.reference_data.xarr.rio.clip([clip_poly], self.viewer_state.reference_data.xarr.rio.crs)

            # TODO: Currently we always just average over the polygon, but maybe we want something else?
            region_mean = region_clip.mean(["longitude", "latitude"]).compute()

            ds = region_mean.to_pandas().resample('1H').mean().dropna()
            print(f"ds: {ds}")
            ds.index = ds.index.tz_localize('UTC').tz_convert(tz)
            seasons = month_to_season_lu[ds.index.month]
            df = pd.DataFrame({'Day': ds.index.date, 
                               'Local Hour': ds.index.hour, 
                               'Nitrogen Dioxide Tropospheric Column Density (10^16 / cm^2)': ds.values,  
                               'Day of Week': ds.index.weekday,
                               'Season': seasons})
            df['Day Type'] = df.apply(weekend_or_holiday, axis=1)
            print(f"df: {df}")
            self._profile_cache = df
        else:
            self._profile_cache = None
