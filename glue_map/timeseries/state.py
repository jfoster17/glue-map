from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.core.data import Data
import pandas as pd
import pickle
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
        # This is a hack for TEMPO data
        with open('city_data.pkl', 'rb') as f:
            self.city_data = pickle.load(f)
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
            self.linewidth = 0
            self.alpha = 0.0
            self.visible = False
        else:
            self.alpha = 1.0
            self.linewidth = 2
            self.as_steps = False

    def reset_cache(self, *args):
        # If this is a subset for a region that is already cached
        # we simply return the cached profile. Doing this basically
        # ignores all the other options in the profile viewer and
        # just relies on the subset label
        if not isinstance(self.layer, Data):
            city_name = self.layer.label
            profile_data = self.viewer_state.city_data.get(city_name, None)
            if profile_data is not None:
                time_local = pd.to_datetime(profile_data['time']).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP[city_name])
                df = pd.DataFrame({"local_hour": time_local.hour, "season": profile_data['time'].dt.season, "data_values": profile_data.values})
                hourly = df.groupby('local_hour').mean('data_values')
                values = hourly['data_values'].values
                axis_values = hourly.index.values
                self._profile_cache = axis_values, values
            else:
                try:
                    region_geom = self.layer.subset_state.roi.to_polygon()
                except AttributeError:
                    self._profile_cache = None
                    return
                clip_poly = Polygon([(x, y) for x, y in zip(region_geom[0], region_geom[1])])
                region_clip = self.viewer_state.reference_data.xarr.rio.clip([clip_poly], self.viewer_state.reference_data.xarr.rio.crs)
                region_mean = region_clip.mean(["longitude", "latitude"])
                profile_data = region_mean.compute()

                time_local = pd.to_datetime(profile_data['time']).tz_localize('UTC').tz_convert(TIMEZONE_LOOKUP['BOS']) # TODO: FIXME!
                df = pd.DataFrame({"local_hour": time_local.hour, "season": profile_data['time'].dt.season, "data_values": profile_data.values})
                hourly = df.groupby('local_hour').mean('data_values')
                values = hourly['data_values'].values
                axis_values = hourly.index.values

                self._profile_cache = axis_values, values
        else:
            self._profile_cache = None
