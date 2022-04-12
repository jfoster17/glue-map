def setup():
    from .map.viewer import IPyLeafletMapView
    from glue_jupyter.registries import viewer_registry
    viewer_registry.add("map",IPyLeafletMapView)