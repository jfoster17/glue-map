import geopandas as gpd
import rioxarray
import xarray as xr
from .data import load_tempo_data
import pickle


def generate_region_data():

    city_mapping = {'NYC': 289, 'LA': 17, 'CHI': 287, 'HOU': 238, 'DC': 292, 'BOS': 86}
    city_data = {'NYC': None, 'LA': None, 'CHI': None, 'HOU': None, 'DC': None, 'BOS': None}

    tempo = load_tempo_data("/Volumes/SanDisk/publicrelease", time_to_int=False)

    bbox = (-155, 17, -24.5, 64)
    urban_areas = gpd.read_file('boundaries/ne_50m_urban_areas/', bbox=bbox)

    for city in city_data.keys():

        urban_geom = urban_areas.loc[city_mapping[city]].geometry
        urban_clip = tempo.xarr.rio.clip([urban_geom], tempo.xarr.rio.crs)
        urban_mean = urban_clip.mean(["longitude", "latitude"])
        yo = urban_mean.compute()
        city_data[city] = yo

    with open('city_data.pkl', 'wb') as f:
        pickle.dump(city_data, f)