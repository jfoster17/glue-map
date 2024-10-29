from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.core.data import Data, BaseData
import pandas as pd
import pickle
from glue.core.exceptions import IncompatibleDataException
from glue.utils import defer_draw

from echo import delay_callback, CallbackProperty, SelectionCallbackProperty
from shapely.geometry import Polygon
__all__ = ['TimeSeriesViewerState', 'TimeSeriesLayerState']


TIMEZONE_LOOKUP = {'NYC': 'America/New_York', 
                   'LA': 'America/Los_Angeles',
                   'CHI': 'America/Chicago',
                   'HOU': 'America/Chicago',
                   'DC': 'America/New_York',
                   'BOS': 'America/New_York'}


class TimeSeriesViewerState(ProfileViewerState):
    # We need to have a start-time and end-time in the state here
    # "2024-10-01 00:00:00"

    t_min = CallbackProperty(docstring='The starting time to show')
    t_max = CallbackProperty(docstring='The ending time to show')
    timezone = SelectionCallbackProperty(docstring='The timezone to use for the time axis')

    _initial_y_scale_done = False

    def __init__(self, **kwargs):
        super().__init__()
        self.x_min = 0
        self.x_max = 24
        timezone_display = {'NYC': 'Eastern', 'CHI': 'Central', 'DEN': 'Mountain', 'LA': 'Pacific'}
        TimeSeriesViewerState.timezone.set_choices(self, ['NYC','CHI','DEN','LA'])
        TimeSeriesViewerState.timezone.set_display_func(self, timezone_display.get)
        #self.add_callback('t_min', self._layers_changed)
        #self.add_callback('t_max', self._layers_changed)
        #self.add_callback('timezone', self._layers_changed)
        self.t_min = "2024-10-15 00:00:00"
        self.t_max = "2024-10-16 00:00:00"
        self.timezone = 'NYC'
        #print("Reference data changed and time params set")

        self.update_from_dict(kwargs)

    def _reset_x_limits(self, *event):

        if self.reference_data is None or self.x_att_pixel is None:
            return

        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = 0
            self.x_max = 24

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


    #def _reference_data_changed(self, before=None, after=None):
    #    print("Reference data changed")
    #    print(f"{before=}")
    #    print(f"{after=}")
        
    #    super()._reference_data_changed(before=before, after=after)
    #    if self.reference_data is not None:
    #        # We SHOULD set the time limits here to something sensible based on the data
    #        # something like:
    #        # self.t_min = self.reference_data['StdTime'].min()
    #        # self.t_max = self.reference_data['StdTime'].max()
    #        # Until we have this in the data object we'll just set
    #        # some default values: FIXME
    #        # self.t_min = "2024-10-01 00:00:00"
    #        # self.t_max = "2024-10-02 00:00:00"
    #        # self.timezone = 'NYC'
    #        # Note that changing these things here properly makes the profile
    #        # recalculate but that _just_ recalculating the profile does NOT
    #        # update the layer artist on the plot
    #        pass


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
        #if self.viewer_state is not None:
        #    self.viewer_state.add_callback('t_min', self.update_profile_with_reset, priority=100000)
        #    self.viewer_state.add_callback('t_max', self.update_profile_with_reset, priority=100000)
        #    self.viewer_state.add_callback('timezone', self.update_profile_with_reset, priority=100000)

    def update_profile_with_reset(self, *args):
        if self.viewer_state.t_min is None:
            return
        if self.viewer_state.t_max is None:
            return
        if self.viewer_state.t_min < self.viewer_state.t_max:
            self.reset_cache()
            self.update_profile(update_limits=False)

    def reset_cache(self, *args):
        #print("Resetting cache...")
        self._profile_cache = None

    def update_profile(self, update_limits=True):
        #print("Calling update_profile")
        #print(f"{self._profile_cache=}")
        if self._profile_cache is not None:
            return self._profile_cache

        if not self.visible:
            return

        #if not self._viewer_callbacks_set:
        #    self.viewer_state.add_callback('x_att', self.reset_cache, priority=100000)
        #    self.viewer_state.add_callback('x_display_unit', self.reset_cache, priority=100000)
        #    self.viewer_state.add_callback('y_display_unit', self.reset_cache, priority=100000)
        #    self.viewer_state.add_callback('function', self.reset_cache, priority=100000)
        #    if self.is_callback_property('attribute'):
        #        self.add_callback('attribute', self.reset_cache, priority=100000)
        #    self._viewer_callbacks_set = True

        if self.viewer_state is None or self.viewer_state.x_att is None or self.attribute is None:
            raise IncompatibleDataException()

        param_list = [self.viewer_state.reference_data, self.viewer_state.t_min, self.viewer_state.t_max, self.viewer_state.timezone]
        #print(f"{param_list=}")
        if any(param is None for param in param_list):
            return

        if not isinstance(self.layer, BaseData):
            
            try:
                x, y = self.layer.subset_state.roi.to_polygon()
                #print(x)
                #print(y)  
            except AttributeError:
                self._profile_cache = [0,0],[0,0]
                return     
            coords = list(zip(x, y))
            polygon = Polygon(coords)

            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0], self.viewer_state.t_min, self.viewer_state.t_max, region=polygon)
            df = df.set_index('StdTime')
            time_local = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP[self.viewer_state.timezone])
            df_new = pd.DataFrame({"local_hour": time_local.hour, "data_values": df['NO2 Troposphere']})
            hourly = df_new.groupby('local_hour').mean('data_values')
            values = hourly['data_values'].values/1e14
            axis_values = hourly.index.values
            #print("This is a subset")
            #print(values)
            #print(axis_values)
            self._profile_cache = axis_values, values
            self.viewer_state.reset_limits()

        else:
            #print("This is a data object")

            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0], self.viewer_state.t_min, self.viewer_state.t_max)
            #print(df)
            df = df.set_index('StdTime')
            time_local = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP[self.viewer_state.timezone])
            df_new = pd.DataFrame({"local_hour": time_local.hour, "data_values": df['NO2 Troposphere']})
            hourly = df_new.groupby('local_hour').mean('data_values')
            values = hourly['data_values'].values/1e14
            axis_values = hourly.index.values
            #print(values)
            #print(axis_values)
            self._profile_cache = axis_values, values
            if not self.viewer_state._initial_y_scale_done:
                self.viewer_state.reset_limits()
                self.viewer_state._initial_y_scale_done = True

    def update_limits(self, update_profile=True):
        pass
        #with delay_callback(self, 'v_min', 'v_max'):
        #    if update_profile:
        #        self.update_profile(update_limits=False)
        #    if self._profile_cache is not None and len(self._profile_cache[1]) > 0:
        #        self.v_min = np.nanmin(self._profile_cache[1])
        #        self.v_max = np.nanmax(self._profile_cache[1])
