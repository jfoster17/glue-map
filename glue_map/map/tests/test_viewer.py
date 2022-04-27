import os
import json 

import pytest
import requests

import numpy as np
from numpy.testing import assert_allclose

import geopandas
import pandas as pd

from glue.core import Data
from glue.core.data_factories import pandas_read_table

from glue_map.data import GeoRegionData, InvalidGeoData

import glue_jupyter as gj


DATA = os.path.join(os.path.dirname(__file__), 'data')

@pytest.fixture
def mapapp(mapdata):
    app = gj.jglue(mapdata=mapdata)
    return app


@pytest.fixture
def capitols():
    capitols = pd.read_csv(DATA+'/state_capitols.txt')
    return Data(capitols,label='capitols')


@pytest.fixture
def cities():
    path_to_data = geopandas.datasets.get_path("naturalearth_cities")
    gdf = geopandas.read_file(path_to_data)
    cities = GeoRegionData(gdf,'cities')
    return cities


@pytest.fixture
def earthdata():
    path_to_data = geopandas.datasets.get_path("naturalearth_lowres")
    gdf = geopandas.read_file(path_to_data)
    earthdata = GeoRegionData(gdf,'countries')
    return earthdata


@pytest.fixture
def mapdata():
    states = geopandas.read_file(DATA+'/us-states.json')
    state_data = pd.read_csv(DATA+'/test_map_data.csv')
    state_data.rename({'ids':'id'},axis=1,inplace=True)
    gdf = pd.merge(states,state_data,on='id')
    mapdata = GeoRegionData(gdf,'states')
    return mapdata


def test_state_with_geopandas(mapapp, earthdata):
    mapapp.add_data(earthdata=earthdata)
    s = mapapp.new_data_viewer('map',data=earthdata)
    print(s.layers[0])
    assert s.layers[0].state.layer_type == 'regions'

def test_make_map_with_data(mapapp, mapdata):
    s = mapapp.new_data_viewer('map',data=mapdata)
    assert len(s.layers) == 1

@pytest.mark.skip(reason='Cannot set state parameters at initialization yet')
def test_make_map_with_data_and_component(mapapp, mapdata):
    print(mapdata.components)
    s = mapapp.new_data_viewer('map',data=mapdata, color= 'Count_Person')
    assert len(s.layers) == 1

@pytest.mark.skip(reason='Cannot set state parameters at initialization yet')
def test_colormap(mapapp, mapdata):
    purple_test_colors = np.array([(0.9882352941176471, 0.984313725490196, 0.9921568627450981, 1.0),
         (0.9372549019607843, 0.9294117647058824, 0.9607843137254902, 1.0),
         (0.8549019607843137, 0.8549019607843137, 0.9215686274509803, 1.0),
         (0.7372549019607844, 0.7411764705882353, 0.8627450980392157, 1.0),
         (0.6196078431372549, 0.6039215686274509, 0.7843137254901961, 1.0),
         (0.5019607843137255, 0.49019607843137253, 0.7294117647058823, 1.0),
         (0.41568627450980394, 0.3176470588235294, 0.6392156862745098, 1.0),
         (0.32941176470588235, 0.15294117647058825, 0.5607843137254902, 1.0),
         (0.24705882352941178, 0.0, 0.49019607843137253, 1.0)])
    s = mapapp.new_data_viewer('map',data=mapdata, color= 'Count_Person', colormap='Purples_09')
    assert s.layers[0].state.colormap == 'Purples_09'
    assert_allclose(s.mapfigure.layers[1].colormap.colors,purple_test_colors)

@pytest.mark.skip(reason='Cannot set state parameters at initialization yet')
def test_empty_map_set_init_and_check_sync(mapapp):
    
    initial_zoom_level = 5
    initial_center = (-40,100)
    
    s = mapapp.new_data_viewer('map',data=None, zoom_level=initial_zoom_level, center=initial_center)
    assert s.state.zoom_level == initial_zoom_level
    assert s.state.center == initial_center
    
    new_zoom_level = 2
    
    s.state.zoom_level = new_zoom_level
    assert s.mapfigure.zoom == s.state.zoom_level
    assert list(s.mapfigure.center) == list(s.state.center)


def test_empty_map(mapapp):
    s = mapapp.new_data_viewer('map',data=None)
    assert len(s.layers) == 0


def test_adding_data_to_empty_map(mapapp, mapdata):
    s = mapapp.new_data_viewer('map',data=None)
    s.add_data(mapdata)
    assert len(s.layers) == 1
    