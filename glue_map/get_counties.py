import datacommons_pandas as dc
import pickle

counties = dc.get_places_in(['geoId/06'], 'County')['geoId/06']
def get_names_for_place_ids(place_id_list):
    """
    This function takes as input a list of place ids and returns the corresponding place names from the Data Commons Graph
    This is oddly slow
    """
    try:
        # get the place names for non-country GEO-LEVELS
        place_name_list = [dc.get_property_values([place_id], 'name')[place_id][0] for place_id in place_id_list]
    except:
        place_name_list = dc.get_property_values([_USA], 'name')[_USA]
    return place_name_list
county_names = get_names_for_place_ids(counties)
county_dict = {k[:-7]:v for k,v in zip(county_names,counties)}
pickle.dump(county_dict, open('county_dict.pkl','wb'))