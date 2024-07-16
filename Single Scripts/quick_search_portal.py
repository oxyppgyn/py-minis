print('''#####################################################################################
\t\t\tArcGIS Portal Quick Search Tool
#####################################################################################\n''')

from arcgis import GIS
import warnings
from difflib import SequenceMatcher as SM
import pandas as pd
import time
import sys

PORTAL_ITEM_TYPES = ['360 VR Experience','CityEngine Web Scene','Map Area','Pro Map','Web Map','Web Scene','Feature Collection','Feature Collection Template','Feature Service','Geodata Service','Group Layer','Image Service','KML','KML Collection','Map Service','OGCFeatureServer','Oriented Imagery Catalog','Relational Database Connection','3DTilesService','Scene Service','Vector Tile Service','WFS','WMS','WMTS','Geometry Service','Geocoding Service','Geoprocessing Service','Network Analysis Service','Workflow Manager Service','AppBuilder Extension','AppBuilder Widget Package','Code Attachment','Dashboard','Data Pipeline','Deep Learning Studio Project','Esri Classification Schema','Excalibur Imagery Project','Experience Builder Widget','Experience Builder Widget Package','Form','GeoBIM Application','GeoBIM Project','Hub Event','Hub Initiative','Hub Initiative Template','Hub Page','Hub Project','Hub Site Application','Insights Workbook','Insights Workbook Package','Insights Model','Insights Page','Insights Theme','Insights Data Engineering Workbook','Insights Data Engineering Model','Investigation','Knowledge Studio Project','Mission','Mobile Application','Notebook','Notebook Code Snippet Library','Native Application','Native Application Installer','Ortho Mapping Project','Ortho Mapping Template','Solution','StoryMap','Web AppBuilder Widget','Web Experience','Web Experience Template','Web Mapping Application','Workforce Project','Administrative Report','Apache Parquet','CAD Drawing','Color Set','Content Category Set','CSV','Document Link','Earth configuration','Esri Classifier Definition','Export Package','File Geodatabase','GeoJson','GeoPackage','GML','Image','iWork Keynote','iWork Numbers','iWork Pages','Microsoft Excel','Microsoft Powerpoint','Microsoft Word','PDF','Report Template','Service Definition','Shapefile','SQLite Geodatabase','Statistical Data Collection','StoryMap Theme','Style','Symbol Set','Visio Document','ArcPad Package','Compact Tile Package','Explorer Map','Globe Document','Layout','Map Document','Map Package','Map Template','Mobile Basemap Package','Mobile Map Package','Mobile Scene Package','Project Package','Project Template','Published Map','Scene Document','Task File','Tile Package','Vector Tile Package','Explorer Layer','Image Collection','Layer','Layer Package','Pro Report','Scene Package','3DTilesPackage','Desktop Style','ArcGIS Pro Configuration','Deep Learning Package','Geoprocessing Package','Geoprocessing Package (Pro version)','Geoprocessing Sample','Locator Package','Raster function template','Rule Package','Pro Report Template','ArcGIS Pro Add In','Code Sample','Desktop Add In','Desktop Application','Desktop Application Template','Explorer Add In','Survey123 Add In','Workflow Manager Package']
#ARC_ITEM_FIELDS = ['id', 'owner', 'created', 'isOrgItem', 'modified', 'guid', 'name', 'title', 'type', 'typeKeywords', 'description', 'tags', 'snippet', 'thumbnail', 'documentation', 'extent', 'categories', 'spatialReference', 'accessInformation', 'licenseInfo', 'culture', 'properties', 'advancedSettings', 'url', 'proxyFilter', 'access', 'subInfo', 'appCategories', 'industries', 'languages', 'largeThumbnail', 'banner', 'screenshots', 'listed', 'ownerFolder', 'protected', 'numComments', 'numRatings', 'avgRating', 'numViews', 'scoreCompleteness', 'groupDesignations', 'lastViewed']
ARC_ITEM_FIELDS = ['owner','title', 'type','description','tags','snippet','categories','numViews']

def portal_login(url, username, password):
    gis = GIS(url, username, password)
    return gis

def query_by_itemtype(filter_type: str = '', type_filter: list = None, gis = 'gis') -> list:
    '''
    An alternative to `gis.content.search()` that can retrieve data on more than 500 items and filter by item type. `gis.content.advanced_search()` could also be used, but has its own problems.
    `gis`: GIS login object.
        Default: `gis` (global variable)
    `filter_type`: Type of filter to apply for item types. `'Exclude'` to remove listed item types, '`Include`' to only keep the listed item types.
        Accepted Values: `'Exclude'`, `'Include'`, `''`
    '''
    #Get GIS Object
    if gis == 'gis':
        gis = globals['gis']
    
    #Filter Types
    if filter_type == 'Exclude':
        type_filter = [i for i in PORTAL_ITEM_TYPES if i not in type_filter]
    elif filter_type == 'Include':
        type_filter = [i for i in PORTAL_ITEM_TYPES if i in type_filter]
    elif filter_type == '' or type_filter is None:
        type_filter = PORTAL_ITEM_TYPES
    else:
        raise ValueError(f'Correct filter type not specified. Exclude, Include, or an empty string are the only accepted inputs. Your input: {filter_type}.')
    
    #Build Query
    if isinstance(type_filter, list):
        query = '" OR "'.join(type_filter)
    else:
        query = type_filter
    query = f'type: ("{query}")'
    items = gis.content.search(query=f'{query} NOT owner: esri*', max_items=500)

    #Search by User, then by User:Itemtype if Max Items Returned
    if len(items) == 500:
        items = []
        users = gis.users.search(max_users = 10000)
        users = [user for user in users if user.storageUsage != 0]
        for user in users:
            items_by_user = gis.content.search(query=f'{query} owner: {user.username}', outside_org=False, max_items=500)
            if len(items_by_user) == 0:
                pass
            elif len(items_by_user) < 500:
                items.extend(items_by_user)
            elif len(items_by_user) == 500:
                for item_type in type_filter:
                    items_by_type = gis.content.search(query=f'type: {item_type} AND owner: {user.username}', outside_org=False, max_items=500)
                    if len(items_by_type) == 0:
                        pass
                    elif len(items_by_type) == 500:
                        warnings.warn(f'{user.username} has over 500 portal items of a single type. Unable to query all {item_type} items. Items currently queried added to content list.')
                        items.extend(items_by_type)
                    else:
                        items.extend(items_by_type)
    elif len(items) == 0:
        raise Exception('No items returned with current arguements.')
    
    #Fix Duplicates from Esri's Weird Query Method **eye roll**
    check_list = []
    for index, item in reversed(list(enumerate(items))):
        if item.id in check_list or item.type not in type_filter:
            items.pop(index)
        else:
            check_list.append(item.id)

    return items

def portal_match_search(items: list, params: dict, match_type: str = 'Exact', fuzzy_tolerance: float = 0.80):
    '''
    Searches fields for items in ArcGIS Portal that match specific parameters.
    `items`: List of ArcGIS items as the arcgis.gis.item class.
    `params`: A dictionary of field names mapped to values to search against. Field names must be those present in `ARC_ITEM_FIELDS`.
    `search_type`: Type of search to conduct.
        Accepted Values: `'Exact'`, `'Partial'`, `'Fuzzy'`

    Notes:
    - Acts as an "or" operator. Only one condition needs to be met for a value to be returned.
    - When doing non-exact matches, text case (upper/lower) is ignored.
    '''
    #Get Proper Items Object
    matched_items = []
    for item in items:
        for key in params:
                if not isinstance(getattr(item, key), list):
                    value = [getattr(item, key)]
                else:
                    value = getattr(item, key)

                for val in value:
                    if match_type == 'Exact':
                        if val == params[key]:
                            matched_items.append(item)
                            break
                    elif match_type == 'Partial':
                        if params[key].lower() in val.lower():
                            matched_items.append(item)
                            break
                    elif match_type == 'Fuzzy':
                        fuzzy_ratio = SM(None, val.lower(), params[key].lower()).ratio()
                        if fuzzy_ratio >= fuzzy_tolerance:
                            matched_items.append(item)
                            break
                    else:
                        raise ValueError('match_type is not a valid value.')

    return matched_items

# -------------------------------------------
#Configs
url = 'https://geo.epa.ohio.gov/portal'
fuzz_tol = 0.80
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)


#Main Script
allow_pass = False
while allow_pass is False:
    username = input('Input your username: ')
    password = input('Input your password: ')

    print(f'\nLogging in as {username}...')
    try:
        gis = portal_login(url, username, password)
        allow_pass = True
    except Exception as e:
        print(f'An error occurred: {e}\n')

print('Searching for items...')
items = query_by_itemtype(gis = gis)
print(f'{len(items)} portal items downloaded.\n\n')

allow_pass = False
while allow_pass is False:
    print('''Select match type.
1. Exact
2. Partial
3. Fuzzy\n''')
    match_type = input('Match type: ')

    if match_type in ['Exact','Partial','Fuzzy']:
        allow_pass = True
    elif match_type in ['1','2','3']:
        types = {'1':'Exact','2':'Partial','3':'Fuzzy'}
        match_type = types[match_type]
        allow_pass = True
    else:
        print('Invalid match type provided.\n')

    if match_type == 'Fuzzy':
        fuzz_tol2 = input('Fuzzy tolerance (0-1, hit enter to skip): ')
        try:
            fuzz_tol2 = float(fuzz_tol2)
            if fuzz_tol2 <= 0 and fuzz_tol2 >= 1:
                print(f'Invalid number. Defaulting to {str(fuzz_tol)}.\n')
            else:
                fuzz_tol = fuzz_tol2
        except:
            print(f'Defaulting to {str(fuzz_tol)}.')

print('\n')

repeat_match = True
while repeat_match is True:
    allow_pass = False
    while allow_pass is False:
        print('Which field would you like to search?')
        count = 1
        for i in ARC_ITEM_FIELDS:
            print(f'{count}. {i}')
            count += 1

        field = input('\nField: ')

        if field in ARC_ITEM_FIELDS:
            allow_pass = True
        elif field in [i for i,v in enumerate(ARC_ITEM_FIELDS)]:
            field = ARC_ITEM_FIELDS(int(i))
            allow_pass = True
        else:
            print('Invalid field provided.\n')


    search_val = input('Value to search for: ')

    matches = portal_match_search(items = items, params = {field:search_val}, match_type = match_type, fuzzy_tolerance = fuzz_tol)

    print(f'Number of matches found: {len(matches)}\n')

    if len(matches) > 0: # ---------------------------------------------------HERE ----------------------------------------------------
        matches = pd.DataFrame(matches)
        #matches = matches[['title','owner','type','id']]
        #matches['url'] = url + 'l/home/item.html?id=' + matches['id']
        matches = matches[['title','owner','type']] #matches[['title','owner','type','url']]
        print(matches)

    allow_pass = False
    while allow_pass is False:
        repeat_match = input('Would you like to search again (Y/N): ')
        try:
            if repeat_match.lower() in ['y','yes']:
                repeat_match = True
                allow_pass = True
            elif repeat_match.lower() in ['n','no']:
                repeat_match = False
                allow_pass = True
            else:
                print('Invalid value.')
        except:
            print('Invalid value.')

print('Exiting matching script...')
time.sleep(2)
sys.exit()
