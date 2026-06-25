"""
Wrappers for easily accessing NPS API services.
"""

import requests

def nps_unit_list() -> list:
    """
    Returns a list of National Park Service (NPS) unit codes.
    """
    unit_list_url = 'https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/FeatureServer/0/query?where=1%3D1&outFields=UNIT_CODE&f=json'
    request = requests.get(unit_list_url, timeout = 20)
    unit_list_data = request.json()
    park_units = []
    
    for item in unit_list_data['features']:
        park_units.append(item['attributes']['UNIT_CODE'])
    
    return park_units

def npspecies_api(park_units: list or str or None = None, categories: list or str or None = None, list_type: str = 'checklist') -> list:
    """
    Returns records in the NPSpecies (v3) database for specified park units. If no units are provided, all data is retrieved.

    Params:
    * `park_units`: List of NPS unit codes. A string can also be used for a single unit.
    * `Categories`: List of species categories to filter on. A string can also be used for a single category.
        * Accepted Values: `'Vascular Plant'`, `'Reptile'`, `'Amphibian'`, `'Fish'`, `'Mammal'`, `'Bird'`
        * Default: `None`
    * `list_type`: Type of data to return.
        * Accepted Values: `'checklist'`,`'detaillist'`,`'fulllist'`
        * Default: `'checklist'`
    * `print_progress`: Whether to print the position in `park_units`, name of park units, and number of records. Useful for seeing the time remaining when getting data for many units.
        * Default: `True`

    Notes:
    * Due to how the NPSpecies API functions, category values can be passed as upper/lower case and the values 1-5 can also be used and correlate to a specific category.
    """

    base_url = 'https://irmaservices.nps.gov/NPSpecies/v3/rest/' + list_type + '/'
    park_data = []

    #Get Park Unit List/Format
    if park_units is None:
        park_units = nps_unit_list()
    elif isinstance(park_units, str):
        park_units = [park_units]

    #Format Categories
    if categories is not None:
        if isinstance(categories, list):
            categories = categories.join(',')
        categories = categories.replace(' ','%20')
        categories = '/' + categories
    else:
        categories = ''

    #API Request
    for unit in park_units:
        unit_url = base_url + unit + categories + '?&format=Json'
        request = requests.get(unit_url, timeout = 45)
        if request.status_code == 200:
            unit_data = request.json()
            park_data = park_data + unit_data

    return park_data
