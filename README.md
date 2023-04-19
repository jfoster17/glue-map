# glue map
A plug-in for [glue-jupyter](https://github.com/glue-viz/glue-jupyter) for the loading and analysis of geospatial data. This plug-in uses [geopandas](https://geopandas.org/en/stable/) to load almost any vector-based spatial data format (ESRI shapefile, GeoJSON files and more) and uses [ipyleaflet](https://ipyleaflet.readthedocs.io/en/latest/) to provide an interactive map that is coupled to other displays of your data so that selections propagate using the brushing and linking paradigm of the [glue visualization library](http://glueviz.org).

You can use glue-map and glue-jupyter for analysis within a Jupyter Lab session and you can transform your Jupyter notebook into a standalone website using [voila](https://voila.readthedocs.io/en/stable/) and [voila-gridstack](https://github.com/voila-dashboards/voila-gridstack). 

## Features

- Read almost any vector-based spatial data format (shapefile, GeoJSON, etc) using the [geopandas](https://geopandas.org/en/stable/) library
- View and interact with your data in a variety of ways: map, 2D scatter, 1D histogram
- Overplot point-like tabular data (e.g. from a CSV) on a map alongside other spatial data
- Create subsets from the map viewer and see how those subsets propagate to other viewers, or see how subsets in other views translate to spatial regions on the map.
- Export your customized Map Viewer to a standalone [leaflet.js](https://leafletjs.com) script for easy embedding in static webpages.
- Serve a complicated Jupyter Lab session as a standalone website using [voila](https://voila.readthedocs.io/en/stable/) and [voila-gridstack](https://github.com/voila-dashboards/voila-gridstack).  

## Install

`pip install git+https://github.com/jfoster17/glue-map.git`


## Example

![Idalmis-demo](https://user-images.githubusercontent.com/3639698/215539329-6b752e63-789d-4fda-8fcd-f7ecfdeeed51.png)


## Testing Commands
Since we cannot easily get error messages from glue-jupyter when a plug-in fails to load, do this:
`python -c 'from glue_map import setup; setup()'` to verify that this plug-in can load.
