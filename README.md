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

Because several of the underlying packages require very specific versions to work together, the easiest way to get a fully functional environment that includes voila and voila-gridstack for layout is to use conda/mamba to install this plug-in into a new virtual environment.

First, grab the repository code:

`git clone https://github.com/jfoster17/glue-map.git`

Then create a new virtual environment using `conda` or `mamba`:

`conda env create -c conda-forge -f environment.yml`

Activate the new environment:

`conda activate glue-map-with-voila-gridstack`

Alternatively, if you already have a working environment for glue-jupyter you can simply do:

`pip install git+https://github.com/jfoster17/glue-map.git`


## Example

A sample notebook is included in notebooks/glue-map-demo.ipynb

This notebook is configured for use with voila-gridstack to enable better layout of multiple viewers. With the recommended environment, you can show the gridstack layout from within jupyter lab as shown below.

![Show-in-voila](https://user-images.githubusercontent.com/3639698/233699762-7f8a17c7-e76a-42b6-ab4b-489201f4d703.gif)

Alternatively you can invoke directly from the command line as:

`voila glue-map-demo.ipynb --template=gridstack`

To edit the existing layout, including adding different viewers or changing their position, user the button highlighted in red within jupyter-lab to change the layout:
![configure-layout](https://user-images.githubusercontent.com/3639698/233700436-bdec620e-7e11-4f86-a0cb-7de1ddfdd065.png)

Another example:

![Idalmis-demo](https://user-images.githubusercontent.com/3639698/215539329-6b752e63-789d-4fda-8fcd-f7ecfdeeed51.png)

## Testing Commands
Since we cannot easily get error messages from glue-jupyter when a plug-in fails to load, do this:
`python -c 'from glue_map import setup; setup()'` to verify that this plug-in can load.
