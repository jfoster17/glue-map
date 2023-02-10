from glue.core import Data


def get_geom_type(layer):
    """
    Get the type of map-like data in layer

    """
    if layer is not None and layer.ndim == 1:
        if isinstance(layer, Data):
            try:
                geom_type = layer.geometry.geom_type
            except AttributeError:
                layer_type = "points"
        else:
            try:
                geom_type = layer.data.geometry.geom_type
            except AttributeError:
                layer_type = "points"
        try:
            layer_type = "regions"
            if (geom_type == "Point").all():
                layer_type = "points"
            elif (geom_type == "LineString").all():
                layer_type = "lines"
        except:  # noqa 722
            layer_type = "points"
        return layer_type
    else:
        return None
