import geopandas
from glue.config import data_translator
from glue.core.component_id import ComponentIDList, ComponentIDDict, ComponentID
from glue.core.data import Data, BaseCartesianData
from glue.core.subset import Subset
from glue.core.coordinates import Coordinates
from datetime import datetime
import numpy as np
import xarray as xr
import glob
import requests
import pandas as pd

import warnings
warnings.filterwarnings('ignore') # setting ignore as a parameter

__all__ = ["InvalidGeoData", "GeoRegionData", "GeoPandasTranslator", "GriddedGeoData", "RemoteGeoData_ArcGISImageServer"]

def convert_from_milliseconds(milliseconds_since_epoch):
    """Converts milliseconds since epoch to a date-time string in 'YYYY-MM-DD HH:MM:SS' format."""
    dt = datetime.fromtimestamp(milliseconds_since_epoch / 1000)
    date_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    return date_time_str

def convert_to_milliseconds(date_time_str):
    """Converts a date-time string in 'YYYY-MM-DD HH:MM:SS' format to milliseconds since epoch."""
    dt = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
    milliseconds_since_epoch = int(dt.timestamp() * 1000)
    return milliseconds_since_epoch


class GriddedGeoData(BaseCartesianData):
    """
    A glue Data class for regularly gridded geospatial data.

    A GriddedGeoData object is 3D with two spatial dimensions and one
    temporal dimension. The spatial dimensions are typically longitude
    and latitude.
    """

    def get_temporal_data(self, cid, region=None, agg_function='mean'):
        """
        Given a region over the spatial dimensions, apply agg_function
        to the data within that region and return the result as a
        1D array. We use this in the TracesViewer to plot time series
        of data within a region. The main differences from the generic
        get_data() method are that we are aggregating over the spatial
        region (and thus returning a 1D array), that region is a
        Shapely object (rather than a view).
        
        This is a method that needs to be implemented by
        subclasses.

        Parameters
        ----------
        cid : :class:`~glue.core.component_id.ComponentID`
            The component ID to use when
        region : :class:`~shapely.geometry.base.BaseGeometry`
            The region over which to aggregate the data.
        agg_function : {'mean', 'median', 'sum', 'std', 'min', 'max'}
            The aggregation function to apply to the data within the region.

        Returns
        -------
        temporal_data : :class:`~numpy.ndarray`
            The actual temporal_data along with the time axis.
        """
        raise NotImplementedError()

    def get_image_url(self, cid, time_index=0):
        """
        Given a time_index, return a URL where an image of that
        data can be retrieved as a PNG for use in
        ImageOverlay. We use this in the MapViewer to display a
        snapshot of the data at a given time.

        This is a method that needs to be implemented by
        subclasses.

        Parameters
        ----------
        cid : :class:`~glue.core.component_id.ComponentID`
            The component ID to use when
        time_index : int
            The index of the time axis to use.

        Returns
        -------
        image : :class:`~numpy.ndarray`
            The image data.
        """
        raise NotImplementedError()


class RemoteGeoData_ArcGISImageServer(BaseCartesianData):
    """
    A glue Data class for remote geospatial data accessed via an ArcGIS ImageService.

    An ArcGIS ImageService is a web service that provides access to raster data
    as a set of images through the `exportImage` endpoint and provides a set of
    samples for a given region and time range through the `getSamples` endpoint.

    image_service_url = "https://arcgis.asdc.larc.nasa.gov/server/rest/services/POWER/power_901_monthly_meteorology_utc/ImageServer"
                        "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN_BETA/ImageServer"
                        "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/"


    Parameters
    ----------
    image_service_url : str
        The URL of the ArcGIS ImageService to access.


    """

    def __init__(self, image_service_url, name=None, **kwargs):
        self.url = image_service_url
        if name:
            self.name = name
        else:
            self.name = image_service_url
        # We need to set up cids for the data components
        # and the component names for use in access functions
        #multidimensionalInfo_url = self.url + "/multiDimensionalInfo"
        #response = requests.get(multidimensionalInfo_url)
        #multidimensionalInfo = response.json()
        #main_component_vars = multidimensionalInfo["variables"]
        #time_component_name = multidimensionalInfo["dimensions"]["name"]
        #time_component_values = multidimensionalInfo["dimensions"]["values"]
        super().__init__(**kwargs)
        self.id = ComponentIDDict(self)
        self._main_components = [ComponentID(label="TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN_BETA",)] #FIXME How do we get this from the ImageServer?

    def get_time(self, tstart, tend):
        """
        Get the time range for an image from the Image Server.
        
        This should be a list of strings running from the start time to the end time.
        """
        return [tstart, tend]

    def get_rendering_rule(self, colorscale):
        """
        Get the rendering rule for an image from the Image Server.

        Parameters:
        colorscale : str
            The name of the color scale to use for the rendering rule.
        """

        rendering_rule_standard_colorramp = {
            "rasterFunctionArguments": {
                "ColorrampName": f"{colorscale}",  #preset ColorRamp from ArcGIS
                "Raster": {
                    "rasterFunctionArguments": {
                        "StretchType": 5,
                        "Statistics": [self.compute_statistic(None, None)], # min value is 0, max value is 3e+16
                        "DRA": False,
                        "UseGamma": False,
                        "Gamma": [1],
                        "ComputeGamma": True,
                        "Min": 0,
                        "Max": 255
                    },
                    "rasterFunction": "Stretch",
                    "outputPixelType": "U64", # must coincide with parameter's pixel type
                    "variableName": "Raster"
                }
            },
            "rasterFunction": "Colormap",
            "variableName": "Raster"
        }
        return rendering_rule_standard_colorramp

    def translate_region(self, region):
        """
        Translate a Shaeply region to an esriGeometryPolygon string.
        """
        if region is None:
            return None
        if region.geom_type == 'Polygon':
            return f'{{"rings":[{list(region.exterior.coords)}],"spatialReference":{{"wkid":4326}}}}'
        elif region.geom_type == 'MultiPolygon':
            return f'{{"rings":[{[list(p.exterior.coords) for p in region]}],"spatialReference":{{"wkid":4326}}}}'
        else:
            raise ValueError("Region must be a Polygon or MultiPolygon")

    def get_temporal_data(self, cid, start_time, end_time, region=None, agg_function='mean'):
        """
        Parameters
        ----------
        cid : :class:`~glue.core.component_id.ComponentID`
            The component ID to use when getting the temporal data. The label
            of this component should be the name of the variable in the ArcGIS ImageServer.
        start_time : str
            The start time in 'YYYY-MM-DD HH:MM:SS' format (UTC).
        end_time : str
            The end time in 'YYYY-MM-DD HH:MM:SS' format (UTC).

        """
        start_time_ms = convert_to_milliseconds(start_time)
        end_time_ms = convert_to_milliseconds(end_time)
        variable_name = cid.label
        esri_region = self.translate_region(region)
        params = {
            "geometry": f"{esri_region}",
            "geometryType": "esriGeometryPolygon",
            "sampleDistance": "",
            "sampleCount": "",
            "mosaicRule": f'{{"multidimensionalDefinition":[{{"variableName":"{variable_name}"}}]}}',
            "pixelSize": "",
            "returnFirstValueOnly": "false",
            "interpolation": "RSP_BilinearInterpolation",
            "outFields": "",
            "sliceId": "",
            "time": f"{start_time_ms},{end_time_ms}",
            "f": "pjson"
        }

        getSamples_url = self.url + "/getSamples"
        response = requests.post(getSamples_url, params=params)
        data = response.json()

        samples = [{
            "StdTime": sample["attributes"]["StdTime"],
            variable_name: float(sample["attributes"][variable_name])
        } for sample in data["samples"] if "attributes" in sample]

        df = pd.DataFrame(samples)

        # Convert StdTime from Unix timestamp (milliseconds) to datetime
        df['StdTime'] = pd.to_datetime(df['StdTime'], unit='ms')

    def get_image_url(self, cid):
        """
        If we call this from the MapViewer we will be calling the
        actual cid to display, so we will have the name directly

        What happens with exportImage if we have a larger time range?

        Parameters
        ----------
        cid : :class:`~glue.core.component_id.ComponentID`
            The component ID to visualize. The label of this component
            should be the name of the variable in the ArcGIS ImageServer.

        """
        exportImage_Url = self.url + f"{cid.label}"+"/ImageServer"
        return exportImage_Url

    def compute_histogram(self, cids, weights=None, range=None, bins=None, log=None, subset_state=None):
        pass

    def compute_statistic(self, statistic, cid, subset_state=None, axis=None, finite=True, positive=False, percentile=None, view=None, random_subset=None):
        """
        Get a statistic for a given component ID, which we can do by calling out to the
        ImageServer.
        """
        stats = [0, 30000000000000000, 910863682171422.1, 9474291611234248] # FIXME
        return stats

    @property
    def label(self):
        return self.name

    def get_kind(self, cid):
        return 'numerical'

    def get_mask(self, subset_state):
        pass

    @property
    def main_components(self):
        return self._main_components

    @property
    def shape(self):
        return (1, )


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
