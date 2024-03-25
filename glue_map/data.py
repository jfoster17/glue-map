import geopandas
from glue.config import data_translator
from glue.core.component_id import ComponentIDList
from glue.core.data import Data
from glue.core.subset import Subset
from glue.core.coordinates import Coordinates
from datetime import datetime
import numpy as np
import xarray as xr
import glob

import warnings
warnings.filterwarnings('ignore') # setting ignore as a parameter

__all__ = ["InvalidGeoData", "GeoRegionData", "GeoPandasTranslator"]


def load_tempo_data(directory, quality_flag='high', sample=False, time_to_int=False):
    """
    Read all the TEMPO datafiles from a given directory into a glue data object
    """
    input_files = glob.glob(f"{directory}/TEMPO_NO2_L3_V01_*_S*.nc")
    # sort input_files by datetime
    input_files.sort()
    if sample:
        input_files = input_files[0:10]
    input_data = []
    datetimes = []
    for input_file in input_files:
        datetimestring = input_file.split('_')[-2]
        datetimes.append(datetime.strptime(datetimestring, '%Y%m%dT%H%M%SZ'))
        coords = xr.open_dataset(input_file, engine='h5netcdf', chunks='auto')
        product = xr.open_dataset(input_file, engine='h5netcdf', chunks='auto', group='product')
        geoloc = xr.open_dataset(input_file, engine='h5netcdf', chunks='auto', group='geolocation')
        support = xr.open_dataset(input_file, engine='h5netcdf', chunks='auto', group='support_data')
        product = product.assign_coords(coords.coords)
        high_quality = (geoloc['solar_zenith_angle'] < 80) & (product['main_data_quality_flag'] == 0) & (support['eff_cloud_fraction'] < 0.2)
        med_quality = (geoloc['solar_zenith_angle'] < 80) & (product['main_data_quality_flag'] == 0) & (support['eff_cloud_fraction'] < 0.4)
        low_quality = (geoloc['solar_zenith_angle'] < 80) & (product['main_data_quality_flag'] == 0)
        if quality_flag == 'high':
            masked_product = product.where(high_quality)
        elif quality_flag == 'medium':
            masked_product = product.where(med_quality)
        elif quality_flag == 'low':
            masked_product = product.where(low_quality)
        input_data.append(masked_product)
    final_data = xr.combine_by_coords(input_data)
    _ = final_data.rio.write_crs("epsg:4326", inplace=True)
    final_data['vertical_column_troposphere'].name = 'NO2'
    new_data = final_data['vertical_column_troposphere']
    new_data = new_data.rio.write_nodata(np.nan, encoded=True)
    no2_norm = 10**16
    new_data.data = new_data.data/no2_norm
    if time_to_int:
        new_data.coords['time'] = range(len(new_data.coords['time']))  # glue needs pixel coordinates to be integers. FIXME! 
    return XarrayData(new_data, label='tempo_no2', coords=XarrayCoordinates(new_data, n_dim=3)), datetimes


class InvalidGeoData(Exception):
    pass

class XarrayCoordinates(Coordinates):
    """
    A work-in-progress class to provide access to xarray coordinates.
    Currently interpolates between pixel and world coordinates, which
    is probably inefficient.

    Does not yet handle units.
    Needs input arrays to be longitude, latitude, time, etc.
    """
    def __init__(self, xarr, **kwargs):

        # This is more principled, but we actually want to enforce
        # longitude, latitude, other order

        #vals = xarr.indexes.values()
        #coords = xarr.coords.keys()

        # So for now we hard-code this. FIXME!!
        coords = ["longitude", "latitude", "time"]
        vals = [xarr[coord].values for coord in coords]

        self.wc = [np.asarray(w).astype(float, casting='unsafe') for w in vals]
        self.pc = [np.arange(len(wc)) for wc in self.wc]
        self.coord_keys = coords
        #self.units = []
        #for coord in self.coord_keys:
        #    try:
        #        self.units.append(xarr[coord].units.split('_')[0][:-1]) #HACK
        #    except AttributeError:
        #        self.units.append("")

        super().__init__(**kwargs)
    
    def pixel_to_world_values(self, *args):
        world_values = tuple([np.interp(arg, self.pc[i], self.wc[i]) for i,arg in enumerate(args)])
        return world_values
    
    def world_to_pixel_values(self, *args):
        pixel_values = tuple([np.interp(arg, self.wc[i], self.pc[i]) for i, arg in enumerate(args)])
        return pixel_values

    #@property
    #def world_axis_units(self):
    #    # Returns an iterable of strings giving the units of the world
    #    # coordinates for each axis.
    #    return self.units

    @property
    def world_axis_names(self):
        # Returns an iterable of strings giving the names of the world
        # coordinates for each axis.
        return [x for x in self.coord_keys]

crs_string = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'

class XarrayData(Data):
    """
    A class to access Xarrays through glue.

    We retain a reference to the original xarray dataset so that we
    can plot it directly in xarray-leaflet.

    We force the crs to be WGS84, which is the only crs natively?
    supported by xarray-leaflet. This should be a conversion, but
    we need something in here even if the xarray dataset does not
    specify.

    """
    def __init__(self, input_xarray, label="", coords=None):
        #This might be what we need for a DataSet
        #components = {x:input_xarray[x].data for x in input_xarray.data_vars.variables}
        #But for a single DataArray we just do this:
        components = {input_xarray.name:input_xarray.data}
        #_ = input_xarray.rio.write_crs("epsg:4326", inplace=True)
        self.xarr = input_xarray
        super().__init__(label=label, coords=coords, **components)

class GeoRegionData(Data):
    """
    A class to hold descriptions of geographic regions as GeoPandas
    (https://geopandas.org/en/stable/) object, either GeoSeries or
    GeoDataFrame objects. A GeoRegionData object is typically created
    by loading a data file from disk in a format that glue recognizes
    as a GeoPandas object (or explicitly using the GeoPandas data
    loader).

    The main challenges to representing arbitrary GeoPandas objects
    (which may include extended regions defined by shapely {Multi}-Lines
    or {Multi}-Polygons) within glue are: (1) defining coordinate
    attributes that can be used for setting up links and to select
    in viewers for display.

    The current approach is to calculate `representative_points` on
    the geometry column of a GeoPandas object and store these as
    special `_centroid_component_ids`. A more natural choice might
    be to use these attributes as coordinate components but they
    are a bit different from normal coordinate components.

    Currently we call these new attributes centroids, although they
    are GeoPandas `representative_points` because we want to
    guarantee that these points are within regions. Centroid
    is a more intuitive, albeit technically incorrect, name.
    """

    def __init__(self, data, label="", coords=None, **kwargs):
        super(GeoRegionData, self).__init__()
        self.label = label
        self.geometry = None

        self._centroid_component_ids = ComponentIDList()
        # self.coords = GeoRegionCoordinates(n_dim=1)
        if isinstance(data, geopandas.GeoSeries) or isinstance(
            data, geopandas.GeoDataFrame
        ):
            self.geometry = None
            # Naming of centroid is a bit misleading, but easier than representative point
            self.centroids = data.representative_point()
            for i in range(2):
                label = data.crs.axis_info[i].name + " (Centroid)"
                if i == 0:
                    cid = self.add_component(self.centroids.y, label=label)
                elif i == 1:
                    cid = self.add_component(self.centroids.x, label=label)
                self._centroid_component_ids.append(cid)

            if isinstance(data, geopandas.GeoDataFrame):
                self.geometry = data.geometry
                for name, values in data.items():
                    if name != data.geometry.name:  # Is this safe?
                        self.add_component(values, label=name)
                    else:
                        # https://leblancfg.com/unhashable-python-unique-locations-geometry-geodataframe.html
                        self.add_component(
                            values.apply(lambda x: x.wkt).values, label="geometry"
                        )

        else:
            raise InvalidGeoData(
                "Input data needs to be of type"
                "geopandas.GeoSeries or geopandas.GeoDataFrame"
            )
        self.meta["crs"] = data.crs


@data_translator(geopandas.GeoDataFrame)
class GeoPandasTranslator:
    """
    Convert a GeoPandas object to a glue GeoRegionData
    object or reconstruct the native GeoPandas object
    from a GeoRegionData object
    """

    def to_data(self, data):
        return GeoRegionData(data)

    def to_object(self, data_or_subset, attribute=None):
        gdf = geopandas.GeoDataFrame()
        coords = data_or_subset.coordinate_components
        if isinstance(data_or_subset, Subset):
            # These are fake components created just for glue
            centroids = data_or_subset.data._centroid_component_ids
            crs = data_or_subset.data.meta["crs"]
        else:
            # These are fake components created just for glue
            centroids = data_or_subset._centroid_component_ids
            crs = data_or_subset.meta["crs"]

        for cid in data_or_subset.components:
            if (cid not in coords) and (cid not in centroids):
                if cid.label == "geometry":
                    g = geopandas.GeoSeries.from_wkt(data_or_subset[cid])
                    gdf[cid.label] = g
                else:
                    gdf[cid.label] = data_or_subset[cid]
        gdf.set_geometry("geometry", inplace=True)
        gdf.crs = crs
        return gdf


# class GeoRegionCoordinates(Coordinates):
#    """
#    A class to provide access to geographic coordinates
#    """
#    def __init__(self):
#        super(GeoRegionCoordinates, self).__init__()
