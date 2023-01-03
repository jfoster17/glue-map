def setup():
    from .map.viewer import IPyLeafletMapViewer
    from glue_jupyter.registries import viewer_registry
    viewer_registry.add("map",IPyLeafletMapViewer)
    from glue.config import settings
    settings.SUBSET_COLORS = ["#1F78B4","#FF7F00","#E31A1C","#FB9A99"]


    red_to_green = ['#D9838D','#ECDF0B','#7CB6BD','#77A865']
    from glue.config import colormaps
    from matplotlib.colors import ListedColormap
    import matplotlib.cm as cm


    colormaps.add('Reds', cm.Reds)
    colormaps.add('Greens', cm.Greens)
    colormaps.add('Blues', cm.Blues)
    colormaps.add('Purples', cm.Purples)
    colormaps.add('Oranges', cm.Oranges)

    colormaps.add('red_to_green',ListedColormap(red_to_green, name='red_to_green'))