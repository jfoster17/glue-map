def setup():
    from glue_jupyter.registries import viewer_registry

    from .map.viewer import IPyLeafletMapViewer

    viewer_registry.add("map", IPyLeafletMapViewer)
    from glue.config import settings

    settings.SUBSET_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    red_to_green = ["#D9838D", "#ECDF0B", "#7CB6BD", "#77A865"]
    green_to_red = ["#77A865", "#7CB6BD", "#ECDF0B", "#D9838D"]

    powerplants = ['green','cyan','brown','black']

    import matplotlib.cm as cm
    from glue.config import colormaps
    from matplotlib.colors import ListedColormap

    colormaps.add("Reds", cm.Reds)
    colormaps.add("Greys", cm.Greys)
    colormaps.add("Greens", cm.Greens)
    colormaps.add("Blues", cm.Blues)
    colormaps.add("Purples", cm.Purples)
    colormaps.add("Oranges", cm.Oranges)

    colormaps.add("red_to_green", ListedColormap(red_to_green, name="red_to_green"))
    colormaps.add("green_to_red", ListedColormap(green_to_red, name="green_to_red"))

    colormaps.add("powerplants", ListedColormap(powerplants, name="powerplants"))

    colormaps.add("coolwarm", cm.coolwarm)


    from .timeseries.viewer import TimeSeriesViewer
    viewer_registry.add("timeseries", TimeSeriesViewer)


    from .traces.viewer import TracesViewer
    viewer_registry.add("traces", TracesViewer)
