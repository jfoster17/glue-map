import datetime
import pandas as pd
import numpy as np
from shapely.geometry import Polygon

from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.core.data import Data, BaseData
from glue.core.exceptions import IncompatibleDataException
from glue.utils import defer_draw
from echo import delay_callback, CallbackProperty, SelectionCallbackProperty

__all__ = ['TimeSeriesViewerState', 'TimeSeriesLayerState']

TIMEZONE_LOOKUP = {'NYC': 'America/New_York', 
                   'LA': 'America/Los_Angeles',
                   'CHI': 'America/Chicago',
                   'HOU': 'America/Chicago',
                   'DC': 'America/New_York',
                   'BOS': 'America/New_York'}


class TimeSeriesViewerState(ProfileViewerState):
    # For now we have t_date as a string and calculcate
    # t_min and t_max from that. This is a bit of a hack but
    # 'Object of type datetime is not JSON serializable' so 
    # we may be stuck with it.

    # The proper way to handle the timezone is at a UnitConverter
    # and then the infrastucture of the ProfileViewer will probably
    # work as expected. It really is just how we are displaying time.
    # If we aren't selecting regions in TimeSeries we don't need the logic
    # in MatplotlibProfileMixin.apply_roi()
    # But we would need to have the x_att unit be a "real" component with units.

    t_date = CallbackProperty(docstring='The date to display')
    t_min = CallbackProperty(docstring='The minimum time to display')
    t_max = CallbackProperty(docstring='The maximum time to display')

    timezone = SelectionCallbackProperty(docstring='The timezone to use for the time axis')

    _initial_y_scale_done = False

    def __init__(self, **kwargs):
        super().__init__()
        timezone_display = {'NYC': 'Eastern', 'CHI': 'Central', 'DEN': 'Mountain', 'LA': 'Pacific', 'UTC': 'UTC'}
        TimeSeriesViewerState.timezone.set_choices(self, ['NYC', 'CHI', 'DEN', 'LA', 'UTC'])
        TimeSeriesViewerState.timezone.set_display_func(self, timezone_display.get)
        self.t_date = "2024-10-15"
        self.timezone = 'UTC'
        self._update_t_min_t_max()
        self.add_callback('t_date', self._t_date_changed, priority=10000000)

        #self.add_callback('x_display_unit', self._convert_units_x_limits, echo_old=True)
        #print("Reference data changed and time params set")

        self.update_from_dict(kwargs)

    def _t_date_changed(self, *event):
        self._update_t_min_t_max()
        for layer in self.layers:
        #    #print(f"{layer=}")
            layer.update_profile()

    def _update_t_min_t_max(self, *event):
        """
        This assumes that we are always just displaying a single day of data.
        The state object would need to be significantly more complex to handle
        the arbitrary case.
        """
        # print("In _update_t_min_t_max...")
        with delay_callback(self, 't_min', 't_max'):
            self.t_min = pd.to_datetime(self.t_date).strftime('%Y-%m-%d %H:%M:%S')
            self.t_max = (pd.to_datetime(self.t_date)+datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    def _reset_x_limits(self, *event):
        # print("In _reset_x_limits...")
        if self.reference_data is None or self.x_att_pixel is None:
            return

        #with delay_callback(self, 'x_min', 'x_max'):
        #    self.x_min = self.t_min
        #    self.x_max = self.t_max

    @defer_draw
    def _reference_data_changed(self, before=None, after=None):
        #print("Reference data changed")
        #print(f"{before=}")
        #print(f"{after=}")

        # A callback event for reference_data is triggered if the choices change
        # but the actual selection doesn't - so we avoid resetting the WCS in
        # this case.
        if before is after:
            return

        for layer in self.layers:
            #print(f"{layer=}")
            layer.reset_cache()

        # This signal can get emitted if just the choices but not the actual
        # reference data change, so we check here that the reference data has
        # actually changed
        if self.reference_data is not getattr(self, '_last_reference_data', None):
            self._last_reference_data = self.reference_data

            with delay_callback(self, 'x_att'):

                if self.reference_data is None:
                    self.x_att_helper.set_multiple_data([])
                else:
                    self.x_att_helper.set_multiple_data([self.reference_data])
                    if self._display_world:
                        self.x_att_helper.world_coord = True
                        self.x_att = self.reference_data.world_component_ids[0]
                    else:
                        self.x_att_helper.world_coord = False
                        self.x_att = self.reference_data.pixel_component_ids[0]
                #print("Calling _update_att...")
                self._update_att()

        #print("Calling reset_limits...")
        #self.reset_limits()
        #print("Limits are reset...")


class TimeSeriesLayerState(ProfileLayerState):

    _viewer_callbacks_set = False
    _layer_subset_updates_subscribed = False
    _profile_cache = None

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state)
        if isinstance(layer, Data):
            #  This makes a data layer invisible at the start
            # This is not what we want if we are restoring a session
            # And turning the layer visible for the first time does
            # not refresh the zoom of the plot to show the new profile
            # data
            self.linewidth = 1.0
            self.alpha = 1.0
            self.visible = True
        else:
            self.alpha = 1.0
            self.linewidth = 2
            self.as_steps = False

    def reset_cache(self, *args):
        # print("Resetting cache...")
        self._profile_cache = None

    def update_profile(self, update_limits=True):
        # print("Calling update_profile")
        # print(f"{self._profile_cache=}")
        if self._profile_cache is not None:
            return self._profile_cache

        if not self.visible:
            return
    
        if not self._viewer_callbacks_set:
            self.viewer_state.add_callback('t_date', self.reset_cache, priority=100000000)
            self._viewer_callbacks_set = True

        if self.viewer_state is None or self.viewer_state.x_att is None or self.attribute is None:
            raise IncompatibleDataException()

        param_list = [self.viewer_state.reference_data, self.viewer_state.t_min, self.viewer_state.t_max, self.viewer_state.timezone]
        if any(param is None for param in param_list):
            return

        if not isinstance(self.layer, BaseData):
            
            try:
                x, y = self.layer.subset_state.roi.to_polygon()
            except AttributeError:
                #print("Got an attribute error")
                self._profile_cache = None
                return     
            coords = list(zip(x, y))
            polygon = Polygon(coords)

            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0],
                                                   self.viewer_state.t_min,
                                                   self.viewer_state.t_max,
                                                   region=polygon)
            agg = df.groupby(by='StdTime').agg({'NO2_Troposphere': np.nanmean})
            values = agg['NO2_Troposphere'].values/1e14
            axis_values = agg.index.values
            #print("This is a subset")
            self._profile_cache = axis_values, values
            self.viewer_state.reset_limits()

        else:
            # print("This is a data object")

            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0],
                                                   self.viewer_state.t_min,
                                                   self.viewer_state.t_max)
            #print(df)
            agg = df.groupby(by='StdTime').agg({'NO2_Troposphere': np.nanmean})
            #print(agg)
            values = agg['NO2_Troposphere'].values/1e14
            axis_values = agg.index.values
            self._profile_cache = axis_values, values
            if not self.viewer_state._initial_y_scale_done:
                self.viewer_state.reset_limits()
                self.viewer_state._initial_y_scale_done = True

    def update_limits(self, update_profile=True):
        pass
