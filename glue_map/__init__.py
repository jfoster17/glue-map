def setup():
    from .map.viewer import IPyLeafletMapViewer
    from glue_jupyter.registries import viewer_registry
    viewer_registry.add("map",IPyLeafletMapViewer)