from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.core.data import Data, BaseData
import pandas as pd
import pickle
from glue.core.exceptions import IncompatibleDataException

from echo import delay_callback
from shapely.geometry import Polygon
__all__ = ['TimeSeriesViewerState', 'TimeSeriesLayerState']


TIMEZONE_LOOKUP = {'NYC': 'America/New_York', 
                   'LA': 'America/Los_Angeles',
                   'CHI': 'America/Chicago',
                   'HOU': 'America/Chicago',
                   'DC': 'America/New_York',
                   'BOS': 'America/New_York'}


class TimeSeriesViewerState(ProfileViewerState):
    def __init__(self, **kwargs):
        super().__init__()
        self.x_min = 0
        self.x_max = 24

    def _reset_x_limits(self, *event):

        if self.reference_data is None or self.x_att_pixel is None:
            return

        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = 0
            self.x_max = 24


class TimeSeriesLayerState(ProfileLayerState):

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

    def update_profile(self, update_limits=True):

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

        #if self.viewer_state is None or self.viewer_state.x_att is None or self.attribute is None:
        #    raise IncompatibleDataException()

        if not isinstance(self.layer, BaseData):
            if self.viewer_state.reference_data is None:
                return
            
            try:
                x, y = self.layer.subset_state.roi.to_polygon()
                #print(x)
                #print(y)  
            except AttributeError:
                self._profile_cache = [0,0],[0,0]
                return     
            coords = list(zip(x, y))
            polygon = Polygon(coords)

            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0], "2024-10-01 00:00:00", "2024-10-02 00:00:00", region=polygon)
            df = df.set_index('StdTime')
            time_local = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP['BOS']) # TODO: FIXME!
            df_new = pd.DataFrame({"local_hour": time_local.hour, "data_values": df['NO2 Troposphere']})
            hourly = df_new.groupby('local_hour').mean('data_values')
            values = hourly['data_values'].values/1e15
            axis_values = hourly.index.values
            #print("This is a subset")
            #print(values)
            #print(axis_values)
            self._profile_cache = axis_values, values
        else:
            if self.viewer_state.reference_data is None:
                return
            
            df = self.layer.data.get_temporal_data(self.viewer_state.reference_data._main_components[0], "2024-10-01 00:00:00", "2024-10-02 00:00:00")
            df = df.set_index('StdTime')
            time_local = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP['BOS']) # TODO: FIXME!
            df_new = pd.DataFrame({"local_hour": time_local.hour, "data_values": df['NO2 Troposphere']})
            hourly = df_new.groupby('local_hour').mean('data_values')
            values = hourly['data_values'].values/1e15
            axis_values = hourly.index.values
            #print("This is a data object")
            #print(values)
            #print(axis_values)
            self._profile_cache = axis_values, values

    def update_limits(self, update_profile=True):
        pass
        #with delay_callback(self, 'v_min', 'v_max'):
        #    if update_profile:
        #        self.update_profile(update_limits=False)
        #    if self._profile_cache is not None and len(self._profile_cache[1]) > 0:
        #        self.v_min = np.nanmin(self._profile_cache[1])
        #        self.v_max = np.nanmax(self._profile_cache[1])
