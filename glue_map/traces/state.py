from glue.core.hub import HubListener

from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty,
                                           DeferredDrawCallbackProperty as DDCProperty)
from glue.core.data_combo_helper import ComponentIDComboHelper, ComboHelper

from glue.core import BaseData
from glue.core.data_combo_helper import ManualDataComboHelper
from shapely.geometry import Polygon
import shapely
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from timezonefinder import TimezoneFinder
from glue.core.message import SubsetUpdateMessage
from echo import delay_callback

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


class TracesViewerState(MatplotlibDataViewerState):
    """
    A TracesViewer takes a datacube of values (y) over three coordinates (lon, lat, t) and
    plots the mean value value of d versus t for values averaged over some region in x and y.

    We don't currently allow the user to change lon_att, lat_att, or t_att, since we assume
    we can get these from reference_data directly.
    
    """
    y_att = DDSCProperty(docstring='The attribute to plot on the y-axis')
    x_att = DDSCProperty(docstring='The attribute to plot on the x-axis') # Fake

    reference_data = DDSCProperty(docstring='The underlying datacube used to generate the traces.')
    group_var = DDSCProperty(docstring='Data-points will be grouped by this attribute so that each unique value of group_var will produce a single line.')

    x_var = DDSCProperty(docstring='Variable to plot on the x-axis')
    estimator = DDSCProperty(default_index = 0, docstring="Function to use to aggregate data points in each group")
    errorbar = DDSCProperty(default_index = 1, docstring="Whether to show error bars [None, 'std', 'sem', 'pi', 'ci']")

    def __init__(self, **kwargs):
        super().__init__()

        self.ref_data_helper = ManualDataComboHelper(self, 'reference_data')

        self.add_callback('layers', self._layers_changed)

        self.y_att_helper = ComponentIDComboHelper(self, 'y_att', categorical=False)

        self.group_var_helper = ComboHelper(self, 'group_var')
        self.group_var_helper.choices = ['Season', 'Day Type', 'Day']
        self.group_var_helper.selection = 'Season'

        self.x_var_helper = ComboHelper(self, 'x_var')
        self.x_var_helper.choices = ['Local Hour', 'Day of Week', 'Season', 'Day Type']
        self.x_var_helper.selection = 'Local Hour'

        self.estimator_helper = ComboHelper(self, 'estimator')
        self.estimator_helper.choices = ['mean', 'sum', 'median', 'max', 'min']
        self.estimator_helper.selection = 'mean'

        self.errorbar_helper = ComboHelper(self, 'errorbar')
        self.errorbar_helper.choices = [None, 'std', 'sem', 'pi', 'ci']
        self.errorbar_helper.selection = 'std'

        self.x_min = 0
        self.x_max = 24
        self.y_min = 0
        self.y_max = 1

    def _layers_changed(self, *args):

        layers_data = self.layers_data
        layers_data_cache = getattr(self, '_layers_data_cache', [])

        if layers_data == layers_data_cache:
            return

        self.y_att_helper.set_multiple_data(self.layers_data)

        self._layers_data_cache = layers_data
        self.ref_data_helper.set_multiple_data(self.layers_data)
        #self._set_reference_data()

    def reset_limits(self):
        with delay_callback(self, 'x_min', 'x_max', 'y_min', 'y_max'):
            self._reset_x_limits()
            self._reset_y_limits()

    def _reset_y_limits(self, *event):
        for layer in self.layers:
            if layer is not None:
                self.y_min = min(self.y_min, layer.v_min)
                self.y_max = max(self.y_max, layer.v_max)

    def _reset_x_limits(self, *event):
        if self.x_var == 'Local Hour':
            self.x_min = 0
            self.x_max = 24
        else: # Temporary default. FIXME
            self.x_min = 0
            self.x_max = 24


class TracesLayerState(MatplotlibLayerState, HubListener):
    """
    This class holds the state for a single layer in a TracesViewer.

    If is strongly inspired by the ProfileLayerState in glue-jupyter, but we have
    to make some changes to account for the fact that we are plotting multiple
    lines on the same plot.
    """

    # Technically we could choose an attribute to plot here, for now we assume NO2
    markers_visible = DDCProperty(False, docstring="Whether to show markers")
    line_visible = DDCProperty(True, docstring="Whether to show a line connecting all positions")

    _viewer_callbacks_set = False
    _layer_subset_updates_subscribed = False
    _data_for_display = None

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state, **kwargs)
        self.num_groups = 0
        self.v_min = 0
        self.v_max = 1
        self.viewer_state = viewer_state
        self.df = None
        self.add_callback('layer', self._on_layer_change, priority=1000)
        self.add_callback('visible', self.reset_data_for_display, priority=1000)

        if layer is not None:
            self._on_layer_change()

        self.update_from_dict(kwargs)

    def _on_layer_change(self, *args):

        if self.layer is not None:

            # We only subscribe to SubsetUpdateMessage the first time that 'layer'
            # is not None, and then do any filtering in the callback function.
            if not self._layer_subset_updates_subscribed and self.layer.hub is not None:
                self.layer.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)
                self._layer_subset_updates_subscribed = True
        #else:
        #    self.reset_cache()

    def _on_subset_update(self, msg):
        if msg.subset is self.layer:
            #print(f'{msg=}')
            self.reset_cache()

    def reset_cache(self, *args):
        #print("In reset_cache")
        #print(f"{args=}")
        self._data_for_display = None

    @property
    def data_for_display(self):
        #print("Trying to get the data to display...")
        self.reset_data_for_display()
        return self._data_for_display

    def reset_data_for_display(self, *args):
        """
        In the profile viewer, the profile is a single set of x and y values.
        Here, we have multiple groups so _data_for_display is 
        [{name:'group_name', x: [x0, x1, ...], y: [y0, y1, ...], lo_error: [y0lo, y1lo, ...], hi_error: [y0hi, y1hi, ...]}]
        
        Currently this is getting called twice for a new subset,
        but it is exiting immediately the first time, so not too expensive.

        Profile viewer sets the cache (self._data_for_display) to None and then
        simply calls this function when we try to get 

        """

        if not self._viewer_callbacks_set:
            #self.viewer_state.add_callback('y_att', self.reset_cache, priority=100000)
            #self.viewer_state.add_callback('x_var', self.reset_cache, priority=100000)

            self.viewer_state.add_callback('group_var', self.regroup, priority=100000)

            self._viewer_callbacks_set = True

        if self._data_for_display is not None:
            #print("Returning cached data")
            return self._data_for_display

        if not self.visible:
            return

        #print("In reset_data_for_display")
        if not isinstance(self.layer, BaseData):
            #print("This is a subset...")
            try:
                region_geom = self.layer.subset_state.roi.to_polygon()
            except AttributeError:
                self._data_for_display = None
                return
            #print("Doing expensive calculation...")
            clip_poly = Polygon([(x, y) for x, y in zip(region_geom[0], region_geom[1])])
            center = shapely.centroid(clip_poly)
            center_lon, center_lat = center.x, center.y
            ##print(f"center_lon: {center_lon}, center_lat: {center_lat}")
            tz = tf.timezone_at(lng=center_lon, lat=center_lat)
            region_clip = self.viewer_state.reference_data.xarr.rio.clip([clip_poly], self.viewer_state.reference_data.xarr.rio.crs)

            # TODO: Currently we always just average over the polygon, but maybe we want something else?
            region_mean = region_clip.mean(["longitude", "latitude"]).compute()

            ds = region_mean.to_pandas().resample('1H').mean().dropna()
            ##print(f"ds: {ds}")
            ds.index = ds.index.tz_localize('UTC').tz_convert(tz)
            seasons = month_to_season_lu[ds.index.month]
            self.df = pd.DataFrame({'Day': ds.index.date,
                               'Local Hour': ds.index.hour,
                               'vertical_column_troposphere': ds.values, 
                               'Day of Week': ds.index.weekday,
                               'Season': seasons})
            self.df['Day Type'] = self.df.apply(weekend_or_holiday, axis=1)
            #print(f"df: {df}")
            # A separate function because sometimes we only need to regroup
            # (specifically when only group_var changes)
            self.regroup()
            #print(f"{all_data=}")
        else:
            self._data_for_display = None

            #  Nitrogen Dioxide Tropospheric Column Density (10^16 / cm^2)

    def regroup(self, *args):
        if not self.visible:
            return
        if self.df is None:
            return #For instance, if this is a Data layer we have not visualized.

        #print("In regroup")
        dfg = self.df.groupby([self.viewer_state.group_var])
        #print(f"{dfg=}")
        self.num_groups = len(dfg)
        all_data = []
        for name, group in dfg:
            y_att = self.viewer_state.y_att.label
            x_att = self.viewer_state.x_var

            data = group.groupby([x_att])[y_att].aggregate(self.viewer_state.estimator)
            x_data = data.index.values
            y_data = data.values
            if self.viewer_state.errorbar is not None:
                if self.viewer_state.errorbar == "std":
                    error = group.groupby([x_att])[y_att].std().values
                    lo_error = y_data - error
                    hi_error = y_data + error
                elif self._viewer_state.errorbar == "sem":
                    error = group.groupby([x_att])[y_att].sem().values
                    lo_error = y_data - error
                    hi_error = y_data + error
            all_data.append({'name': name, 'x': x_data, 'y': y_data, 'lo_error': lo_error, 'hi_error': hi_error})
        self._data_for_display = all_data
