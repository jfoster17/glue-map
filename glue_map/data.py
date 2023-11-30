import geopandas
import shapely

from glue.config import data_translator
from glue.core.component import ExtendedComponent
from glue.core.data_region import RegionData
from glue.core.subset import Subset

__all__ = ["InvalidGeoData", "GeoRegionData", "GeoPandasTranslator"]


class InvalidGeoData(Exception):
    pass


class GeoRegionData(RegionData):
    """
    A class to hold descriptions of geographic regions as GeoPandas
    (https://geopandas.org/en/stable/) object, either GeoSeries or
    GeoDataFrame objects. A GeoRegionData object is typically created
    by loading a data file from disk in a format that glue recognizes
    as a GeoPandas object (or explicitly using the GeoPandas data
    loader).

    We assume that the GeoPandas object does NOT have centroid coordinates
    for the geometry components, and so we create them manually.

    Parameters
    ----------
    data : GeoPandas object
        A GeoPandas object (GeoSeries or GeoDataFrame)
    label : str, optional
        A label for the data
    coords : :class:`~glue.core.coordinates.Coordinates`, optional
        The coordinates associated with the data.
    **kwargs :
        Any additional keyword arguments are passed to the
        :class:`~glue.core.data.Data` constructor.

    Attributes
    ----------
    geometry : array of `shapely.Geometry`` objects
        The actual shapely geometry objects

    """

    def __init__(self, data, label="", coords=None, **kwargs):
        if not isinstance(data, (geopandas.GeoSeries, geopandas.GeoDataFrame)):
            raise InvalidGeoData(
                "Input data needs to be of type"
                "geopandas.GeoSeries or geopandas.GeoDataFrame"
            )
        else:
            super().__init__(label=label, coords=coords)

            if isinstance(data, geopandas.GeoDataFrame):
                for name, values in data.items():
                    if all(isinstance(s, shapely.Geometry) for s in values):
                        pass
                    else:
                        self.add_component(values, label=name)

            self.centroids = data.representative_point()
            cen_x_id = self.add_component(self.centroids.x, label='Center '+data.crs.axis_info[1].name)
            cen_y_id = self.add_component(self.centroids.y, label='Center '+data.crs.axis_info[0].name)
            if isinstance(data, geopandas.GeoSeries):
                geometries = data
            else:
                geometries = data.geometry
            extended_comp = ExtendedComponent(geometries, center_comp_ids=[cen_x_id, cen_y_id])
            self.add_component(extended_comp, label='geometry')

        self.meta["crs"] = data.crs

    @property
    def _centroid_component_ids(self):
        return [self.center_x_id, self.center_y_id]

    @property
    def geometry(self):
        return self.get_component(self.extended_component_id).data


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
            # These are components created just for glue
            centroids = data_or_subset.data._centroid_component_ids
            extended_cid = data_or_subset.data.extended_component_id
            crs = data_or_subset.data.meta["crs"]
        else:
            # These are components created just for glue
            centroids = data_or_subset._centroid_component_ids
            extended_cid = data_or_subset.extended_component_id
            crs = data_or_subset.meta["crs"]

        for cid in data_or_subset.components:
            if (cid not in coords) and (cid not in centroids):
                if cid == extended_cid:
                    g = geopandas.GeoSeries(data_or_subset[cid].values) # use values to avoid getting the index
                    gdf.set_geometry(g, inplace=True)
                else:
                    gdf[cid.label] = data_or_subset[cid]
        gdf.crs = crs
        return gdf


# class GeoRegionCoordinates(Coordinates):
#    """
#    A class to provide access to geographic coordinates
#    """
#    def __init__(self):
#        super(GeoRegionCoordinates, self).__init__()
