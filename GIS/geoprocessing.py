"""
TEST:
* format_sql_qry added to select_by_index
* format_sql_qry added tosnap_by_attribute

ISSUES:
* Blob and Raster types not defined in ARC_PY_DTYPES
"""
import datetime
from typing import Union
import arcpy

#ArcGIS Field DataTypes and Corresponding Python DataTypes
ARC_PY_DTYPES = {'GlobalID': str, 'Geometry':tuple, 'OID':int, 'Integer':int, 'BigInteger':int,
                 'Single':float, 'Double':float, 'String':str, 'Date':datetime.datetime,
                 'DateOnly':datetime.date, 'TimeOnly':datetime.time, 
                 'TimeStampOffset':datetime.datetime, 'Blob':'???', 'Guid':str,'Raster':'???'}

def format_sql_query(table: str, field: str, values: Union[str|list], invert = False) -> str:
    """
    Infers the correct SQL format from a field's datatype and builds a query 
    with the provided values in the inferred format.
    
    Params:
    * `table`: Table the field used is in.
    * `field`: Field used in query. The datatype from this will be used for formatting.
    * `values`: A list of values to query for. Can be a single value in the form of a string.
    * `invert`: Whether to invert the query.
        * Default: `False`
    
    Notes:
    * `None` (SQL NULL equivalent) values will be removed from value lists to prevent unexpected behavior. 
    If `None` is the only value, an error will  be raised.
    
    Issues:
    * TRUE and FALSE values are currently not formatted correctly from boolean Python values.
    """

    #Get Field Type
    field_type = ARC_PY_DTYPES[[field_type.type for field_type in arcpy.ListFields(table) if field_type.name == field][0]]
    
    #Format Values List
    if isinstance(values, list):
        if len(values) == 1:
            values = values[0]
        else:
            values = [value for value in values if value is not None]
    if values is None:
        raise ValueError('NULL values are not intended to be used in this function due to their potential affects on datasets if queried.')
    
    #Build Query Based on Field Type
    if isinstance(values, list):
        if field_type == str:
            query = f"""{field} IN ({','.join([f"'{val}'" for val in values])})"""
        elif field_type in [int, float]:
            query = f"""{field} IN ({','.join([f"{val}" for val in values])})"""
        elif field_type in [datetime.datetime]:
            query = f"""{field} IN ({','.join([f"timestamp '{val}'" for val in values])})"""
        else:
            raise NotImplementedError(f'This field type is untested. Type: {field_type}')
    else:
        if field_type == str:
            query = f"{field} = '{values}'"
        elif field_type in [int, float]:
            query = f"{field} = {str(values)}"
        elif field_type in [datetime.datetime, datetime.date, datetime.time]:
            query = f"{field} = timestamp '{str(values)}'"
        else:
            raise NotImplementedError(f'This field type is untested. Type: {field_type}')

    #Invert Query
    if invert is True:
        if isinstance(values, list):
            query = query.replace(' IN ', ' NOT IN ')
        else:
            query = query.replace(' = ', ' <> ')

    return query

def count_records(table: str, ignore_selection: bool = True) -> int:
    """
    Returns a count of the number of records in a table or the number of records currently selected.

    Params:
    * `table`: Table with records to be counted.
    * `ignore_selection`: Whether to ignore any current selections. This also bypasses definition queries applied.
        * Default: `True`

    Issues:
    * There is currently no known way to count selected records and account for definition queries.
    """

    #Bypass Selection
    if ignore_selection is True:
        source = lambda in_layer: arcpy.Describe(in_layer).catalogPath
        table = source(table)

    #Try Iterating with Count, Error = End of Table
    with arcpy.da.SearchCursor(table, arcpy.ListFields(table)[0].baseName) as search_cursor:
        count = 0
        while True:
            try:
                next(search_cursor)
                count += 1
            except:
                return count

def select_by_index(table: str, index: Union[int|list], clear_prev_selection: bool = True, id_field: str = 'OBJECTID') -> None:
    """
    Selects record(s) in a table its position in the table matches the index/indices specified.

    Params:
    * `table`: Input table to select from.
    * `index`: List of indices to select. 
    * `clear_prev_selection`: Whether to clear existing selections.
        * Default: `True`
    * `id_field`: Name of field that will be used to search find and select the first record. This field must have unique values for each record.
        * Default: `'OBJECTID'`
    
    Notes:
    * This function obeys any definition queries and selections.
    * Attempting to select by index without clearing the previous selection can fail or cause weird behavior, as it uses only the selected records.
    """

    #Format/Check Index
    if isinstance(index, int):
        index = [index]
    elif not isinstance(index, list):
        raise ValueError('Indices must be an integer or list of integers.')
    
    #Clear Selection
    if clear_prev_selection is True:
            arcpy.management.SelectLayerByAttribute(in_layer_or_view = table, selection_type = 'CLEAR_SELECTION')
    
    #Get Values to Query
    index_list = []
    for i in index:
        with arcpy.da.SearchCursor(table, id_field) as search_cursor:
            iteration = 0
            while iteration < i:
                try:
                    id_value = next(search_cursor)[0]
                    iteration += 1
                except:
                    raise ValueError(f'Table contains {iteration} records. Your index value was: {i}.')
                #print(id_value)
                #print(id_field)
        index_list.append(id_value)
            
    #Format SQL Queries
    query = format_sql_query(table = table, field = id_field, values = index_list, invert = False)
            
    #Select by Attribute
    arcpy.management.SelectLayerByAttribute(in_layer_or_view = table, selection_type = 'NEW_SELECTION', where_clause = query)

def reset_stats_fields(table: str, field_list: Union[list|None] = None, rep_alias: bool = True) -> None:
    """
    **WARNING:** This tool modifies the input table.

    Resets statistics field names after using tools like dissolve.

    Params:
    * `table`: Table to be updated.
    * `field_list`: List of fields to be updated. If `None`, all fields updated.
        * Default: `None`
    * `rep_alias`: If the field alias will be updated. 
        * Default: `True`.
    """

    field_prefixes = ['SUM_','MEAN_','MIN_','MAX_','RANGE_','STD_','COUNT_','FIRST_','LAST_','MEDIAN_','VARIANCE_','UNIQUE_','CONCATENATE_']
    if field_list is None:
        field_list = [field.name for field in arcpy.ListFields(table)]
    for field in field_list:
        if any(item in field for item in field_prefixes):
            rem_val = [item for item in field_prefixes if item in field]
            field_rep = field.replace(rem_val[0],'')
            if rep_alias is True:
                arcpy.management.AlterField(in_table = table, field = field, new_field_name = field_rep, new_field_alias = field_rep)
            else:
                arcpy.management.AlterField(in_table = table, field = field, new_field_name = field_rep)

def list_field_attributes(table: str, fields: Union[list|str], unique_values: bool = False, return_type: Union[str] = dict) -> Union[list|dict]:
    """
    Creates a list or dict of values in table field(s).

    Params:
    * `table`: Table to get values from.
    * `fields`: List of fields to get values from. A string can be used for a single field.
    * `unique_values`: If the returned values should include all values from the field, or only a list of unique values in the field.
        * Default: `False`
    * `return_type`: Type of object to return, list or dictionary.
        * Default: `dict`
        * Accepted Values: `list`, `dict`, `'List'`, `'Dictionary'`
        
    Notes:
    * When returning a list, a list of lists will be returned if more than one field was inputted. If a single field was inputted, a flat list will be outputted.
    * Unique elements are not in the order in the source table, but are ordered according to how items are ordered in Pythonic sets.
    """

    #Check return_type
    if return_type == dict or return_type == 'Dictionary':
        all_attributes = {}
    elif return_type == list or return_type == 'List':
        all_attributes = []
    else:
        raise ValueError('Return type is not a valid value.')
        
    #Format fields
    if isinstance(fields, str):
        fields = [fields]
    
    for field in fields:
        #Get Values for Field With Search Cursor
        with arcpy.da.SearchCursor(table, field) as cursor:
            if unique_values is True:
                attributes =  list({row[0] for row in cursor})
            else:
                attributes =  [row[0] for row in cursor]
        
        #Add to Output
        if return_type == dict or return_type == 'Dictionary':
            all_attributes[field] = attributes
        elif return_type == list or return_type == 'List':
            if len(fields) == 1:
                all_attributes = attributes
            else:
                all_attributes.append(attributes)
            
    return all_attributes

def snap_by_attribute(in_layer: str, snap_layer: str, id_field: Union[str|list|dict], snap_type: str = 'Edge', ignore_values: any = None, distance: str = '1000 Meters') -> list:
    """
    **WARNING**: This tool modifies the input layer.

    Snaps features to another layer based on matching values in an attribute field.

    Params:
    * `in_layer`: Layer to snap to another layer.
    * `snap_layer`: Layer that will be snapped to.
    * `id_field`: Field(s) with attributes to determine snapping. If field names are the same, a string can be used. If fields are different, a list or dict can be used.
    * `snap_type`: Type of snap to perform.
        * Default: `'Edge'`
        * Accepted Values: `'End'`, `'Vertex'`, `'Edge'`
    * `ignore_values`: Value(s) to not attempt snapping with. A list of values or a single value as a string can be provided.
        * Default: `None`
    * `distance`: Distance within which a snap can occur.
        * Default: `'100 Meters'`

    Notes:
    * This tool will never snap based on the value 'NULL' due to how unique attribute values are obtained.
    """

    # Format id_field
    if isinstance(id_field, list):
        id_field_in = id_field[0]
        id_field_snap = id_field[1]
    elif isinstance(id_field, dict):
        id_field_in = id_field.keys()[0]
        id_field_snap = id_field[id_field_in]
    else:
        id_field_in = id_field
        id_field_snap = id_field
    
    # Get List of Unique Values in ID Field & Remove Ignore Values
    unique_ids = list_field_attributes(table = in_layer, fields = id_field_in, unique_values = True, return_type = list)
    if ignore_values is not None:
        if isinstance(ignore_values, list):
            unique_ids = [value for value in unique_ids if value not in ignore_values]
        else:
            unique_ids = [value for value in unique_ids if value != ignore_values]
    
    #Create Snap Environment
    snap_env = f"{snap_layer} {snap_type.upper()} '{distance}'"
    
    # Iterate through Unique Values
    for value in unique_ids:
        ##Format Queries
        query_in = format_sql_query(table = in_layer, field = id_field_in, values = value, invert = False)
        query_snap = format_sql_query(table = snap_layer, field = id_field_snap, values = value, invert = False)

        ##Select By Attribute in Both Layers
        arcpy.management.SelectLayerByAttribute(in_layer_or_view = in_layer, selection_type = 'NEW_SELECTION', where_clause = query_in)
        arcpy.management.SelectLayerByAttribute(in_layer_or_view = snap_layer, selection_type = 'ADD_TO_SELECTION', where_clause = query_snap) 

        ##Snap
        arcpy.edit.Snap(in_features = in_layer, snap_environment = snap_env)
        
        ##Clear Selection for Next Snap
        arcpy.management.SelectLayerByAttribute(in_layer_or_view = in_layer, selection_type = "CLEAR_SELECTION")
        arcpy.management.SelectLayerByAttribute(in_layer_or_view = snap_layer, selection_type = "CLEAR_SELECTION")

def nearest_by_attribute(in_layer: str, near_layer: str, field: Union[str|list|dict], out_table: str, sep: Union[str|None] = None, ignore_values: any = None, near_params: Union[dict|None] = None) -> list:
    """
    Creates a near table for two layers, by attribute.
    
    * `in_layer`: Layer to snap to another layer.
    * `near_layer`: Layer used as the near features.
    * `field`: Field(s) with attributes to determine near IDs. If field names are the same, a string can be used. If fields are different, a list or dict can be used.
    * `sep`: Value seperator for the `in_layer` field. If a seperator is specified, any near feature with one of the resulting substrings will be queried. 
        * Default: `None`
    * `ignore_values`: Value(s) to not attempt snapping with. A list of values or a single value as a string can be provided.
        * Default: `None`
    * `near_params`: 
        * Default: `None`
    
    Notes:
    * `sep` can be useful for determining which feature out of predetermined groups is closest to another feature. 
    * `sep` can be used to find the nearest segment of a specific dissolved feature if an ID field was concatenated upon dissolving.
    """

    #Format field
    if isinstance(field, list):
        field_in = field[0]
        field_near = field[1]
    elif isinstance(field, dict):
        field_in = field.keys()[0]
        field_near = field[field_in]
    else:
        field_in = field
        field_near = field
        
    #Get Near Params
    ##Set Defaults
    params = {'search_radius':None, 'location':'NO_LOCATION', 'angle':'NO_ANGLE','closest':'CLOSEST','closest_count':0, 'method':'PLANAR', 'distance_unit':''}
    
    ##Get Param Values
    if near_params is not None:
        if isinstance(near_params, list):
            for index, i in enumerate(params):
                try:
                    params[i] = near_params[index]
                except:
                    pass
        elif isinstance(near_params, dict):
            for i in params:
                try:
                    params[i] = near_params[i]
                except:
                    pass
        else:
            raise ValueError('near_params is not in an acceptable format.')
            
        ##Format Values
        for i in ['location', 'angle']:
            if params[i] is True or params[i] == i.upper():
                params[i] = i.upper()
            else:
                params[i] = f'NO_{i.upper()}'
        if params['closest'] is True or params['closest'] == 'CLOSEST':
            params['closest'] = 'CLOSEST'
        else:
            params['closest'] = 'ALL'
        params['method'] = params['method'].upper()
    
    #Get List of Unique Values in ID Field & Remove Ignore Values
    unique_ids = list_field_attributes(table = in_layer, unique_values = True, fields = field_in, return_type = list)
    if ignore_values is not None:
        if isinstance(ignore_values, list):
            unique_ids = [value for value in unique_ids if value not in ignore_values and value is not None]
        else:
            unique_ids = [value for value in unique_ids if value != ignore_values and value is not None]
    else:
      unique_ids = [value for value in unique_ids if value is not None]

    #Iterate Through Unique Values
    with arcpy.da.Editor(arcpy.env.workspace) as edit:
        for value in unique_ids:
            #Select by Attribute
            ##Split on sep
            if sep is not None and sep in value:
                near_value = value.split(sep)
            else:
                near_value = value
            
            ##Build Queries
            in_query = format_sql_query(table = in_layer, field = field_in, values = value, invert = False)
            near_query = format_sql_query(table = near_layer, field = field_near, values = near_value, invert = False)
            
            #Select
            arcpy.management.SelectLayerByAttribute(in_layer_or_view = in_layer, selection_type = 'NEW_SELECTION', where_clause = in_query)
            arcpy.management.SelectLayerByAttribute(in_layer_or_view = near_layer, selection_type = 'NEW_SELECTION', where_clause = near_query)

            #Near
            arcpy.analysis.GenerateNearTable(in_features = in_layer,near_features = near_layer, out_table = 'memory/near_by_attr_TEMP',search_radius = params['search_radius'],location = params['location'], 
                angle = params['angle'], closest = params['closest'], closest_count = params['closest_count'], method = params['method'], distance_unit = params['distance_unit'])
            
            #Create Output Table
            if not arcpy.Exists(out_table):
                arcpy.management.CreateTable(out_name = out_table, template = 'memory/near_by_attr_TEMP')
            
            #Add Values to Out Table
            arcpy.management.Append(inputs = 'memory/near_by_attr_TEMP', target = out_table)

            #Clear Selection
            arcpy.management.SelectLayerByAttribute(in_layer_or_view = in_layer, selection_type = "CLEAR_SELECTION", where_clause = "", invert_where_clause = None)
            arcpy.management.SelectLayerByAttribute(in_layer_or_view = near_layer, selection_type = "CLEAR_SELECTION", where_clause = "", invert_where_clause = None)

    #Delete Temp Table When Done
    arcpy.management.Delete(in_data = 'memory/near_by_attr_TEMP')

def poly_intersect_percent(border_layer: str, intersect_layer: str, out_layer: str, area_unit: str = 'SQUARE KILOMETERS'):
    """
    Calculates the areas and percent intersection between two layers as a new feature class. Attributes and geometry from the border layer are preserved.
    Border layer areas will represent the entire polygon, while intersect layer areas are proportional of the area within border layer features.
    
    Params:
    * `border_layer`: Polygon layer representing border features.
    * `intersect_layer`: Polygon layer 
    * `out_layer`: Output polygon layer.
    * `area_unit`: Areal unit feature areas will we calculated in. Not case sensitive, words should be seperated with spaces. 
        * Default: `"SQUARE KILOMETER"`.
        * Accepted Values: Variations in case of: "ACRES","HECTARES","SQUARE METERS","SQUARE KILOMETERS","SQUARE FEET","SQUARE YARDS","SQUARE MILES".
    """
    
    #Validation
    units = ['ACRES','HECTARES','SQUARE METERS','SQUARE KILOMETERS','SQUARE FEET','SQUARE YARDS','SQUARE MILES']
    if area_unit.upper() not in units:
        raise ValueError(f'area_unit is not a valid value.')
    else:
        area_unit = area_unit.upper()

    for layer in [border_layer, intersect_layer]:
        if arcpy.Describe(layer).shapeType != 'Polygon':
            raise arcpy.ExecuteError(f'"{layer}" is not a polygon layer.')
    
    #Calculate Intersect Area
    arcpy.AddMessage('Calculating intersect layer areas...')
    arcpy.analysis.SummarizeWithin(in_polygons = border_layer, in_sum_features = intersect_layer, out_feature_class = out_layer, shape_unit = area_unit.replace(' ',''))
    arcpy.management.AlterField(in_table = out_layer, field = [field.name for field in arcpy.ListFields(out_layer) if 'sum_Area_' in field.name][-1], 
        new_field_name = 'intersect_area', new_field_alias = 'Intersect Area')
    
    #Calculate Border Area
    arcpy.AddMessage('Calculating border layer areas...')
    if area_unit in ['SQUARE FEET','SQUARE MILES']:
        area_unit = f"{area_unit.replace(' ','_')}_INT"
    else:
        area_unit = area_unit.replace(' ','_')
    arcpy.management.CalculateGeometryAttributes(in_features = out_layer, geometry_property = 'border_area AREA_GEODESIC', area_unit = area_unit)
    arcpy.management.AlterField(in_table = out_layer, field = 'border_area', new_field_alias = 'Border Area')
    
    ##Get Area Percentage
    arcpy.AddMessage('Calculating percent intersection...')
    arcpy.management.CalculateField(in_table = out_layer, field = "percent_area_intersect", expression = "area_calc(!border_area!,!intersect_area!)", expression_type = "PYTHON3",
        code_block = 'def area_calc(border, intersect):\n\ttry:\n\t\tarea = intersect/border*100\n\t\treturn area\n\texcept:\n\t\treturn 0', field_type="FLOAT")
    arcpy.management.AlterField(in_table = out_layer, field = 'percent_area_intersect', new_field_alias = 'Percent Intersection')

