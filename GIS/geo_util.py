from typing import Union
import arcpy
from pandas import DataFrame

def py_to_geotable(py_table, geo_table, field_mapping = None) -> None:
    """
    Converts a table-like Python object to an geodatabase table.
    
    Params:
    * `py_table`: Table-like Python object.
    * `geo_table`: Geodatabase table the `py_table` object will be converted to.
    * `field_mapping`: A field mapping string.
        * Default: `None`
    
    Notes:
    * This is a helper function and is used as a method of easily adding 
    validation methods to table conversions in the future.
    
    Issues:
    - This function is exceedingly fragile and currently has no validation 
    procedures.
    """
    df = DataFrame(py_table)
    arcpy.conversion.ExportTable(in_table = df, out_table = geo_table, field_mapping = field_mapping)

def zoom_to_selection(selection_layer: str, scale: Union[str|int|float|None] = None, reset_selection: bool = False) -> Union[int|float]:
    """
    Zooms to the extent of a selected feature. If no features are selected, zooms to the center of the feature.

    Params:
    * `selection_feature`: Map layer with the extent used for zoom in/out.
    * `scale`: Map scale to zoom to. Can be an interger or string representing a scale ratio (`'int:int'`).
        * Default: `None`
    * `reset_selection`: If the current selection should be reset after zooming.
        * Default: `False`

    Issues:
    * Add automatic/dynamic zoom scaling. Currently, zoom is retained or input value is used.
    """

    #Pan to Extent
    current_map = arcpy.mp.ArcGISProject("CURRENT").activeMap
    map_view = arcpy.mp.ArcGISProject("CURRENT").activeView
    map_layer = current_map.listLayers(selection_layer)[0]
    extent = map_view.getLayerExtent(map_layer, True, True)
    map_view.panToExtent(extent)
    
    #Change Scale
    if scale is not None:
        if isinstance(scale,str):
            if ':' in scale:
                scale = scale.split(':')
                scale = int(scale[1])/int(scale[0])
        map_view.camera.scale = scale

    #Reset Selection
    if reset_selection is True:
        arcpy.management.SelectLayerByAttribute(in_layer_or_view = selection_layer, selection_type = "CLEAR_SELECTION", where_clause = "", invert_where_clause = None)
    
    return extent

def convert_fieldmap(fieldmap: str):
    """
    Converts between ArcGIS field mapping strings and list-dict representations of field mappings.

    Params:
    * `fieldmap`: Field mapping string, list-dict representation of mapping, or a layer name. The output of this function is determined by the type of input.
    
    Notes:
    * `fieldmap` dictionaries must include the following keys:'baseName','aliasName','editable','isNullable','required','length','type','scale','precision','mergeRule','joinDelimiter','dataSource','outputField','beginning','end'
    * Building strings from fields uses default values of `#` ("null" equivalent) for `joinDelimiter`, and `-1` for `beginning` and `end`.
    * To build a list-dict from a table name, use this function twice to convert to a string, then to a list-dict.
    """
    
    #Field Names
    string_fields = ['baseName','aliasName','editable','isNullable','required','length','type','scale','precision','mergeRule','joinDelimiter','dataSource','outputField','beginning','end']
    out_fm = []        
    
    if isinstance(fieldmap, str):
        #Check if fieldmap is a Layer Name
        if fieldmap in [lyr.name for lyr in arcpy.mp.ArcGISProject("CURRENT").listMaps()[0].listLayers()]:
            fm_field = arcpy.ListFields(fieldmap)
            for field in fm_field:
                if field.name == 'OBJECTID' or field.name == 'Shape':
                    continue
                fm_field = f'''{getattr(field,string_fields[0])} "{getattr(field,string_fields[1])}" {str(getattr(field,string_fields[2]))} {str(getattr(field,string_fields[3]))} {str(getattr(field,string_fields[4]))} {getattr(field,string_fields[5])} {getattr(field,string_fields[6])} {getattr(field,string_fields[7])} {getattr(field,string_fields[8])},First,#,{fieldmap},{getattr(field,string_fields[0])},-1,-1'''
                out_fm.append(fm_field)
            out_fm = ';'.join(out_fm)
            out_fm = out_fm.replace(' True ',' true ').replace(' False ',' false ').replace(' String ',' Text ')
            
        #Else, Convert From String to List-Dict
        else:
            fm_field = []
            fieldmap = fieldmap.replace('","','<COMMADELIM>').replace('" "','<SPACEDELIM>')
            fieldmap = fieldmap.split(';')
            for item in fieldmap:
                fm_field.append([x for i in item.split(' ') for x in i.split(',')])
            for field in fm_field:
                field_dict = {}
                for index, name in enumerate(string_fields):
                    if index > len(field) - 1:
                        continue
                    value = field[index].replace('"','')
                    if value == 'true':
                        value = True
                    elif value == 'false':
                        value = False
                    elif value == '#':
                        value = None
                    elif value == '<COMMADELIM>':
                        value = ','
                    elif value == '<SPACEDELIM>':
                        value = ' '
                    field_dict[name] = value
                out_fm.append(field_dict) 

    #Convert From List-Dict to String
    elif isinstance(fieldmap, list):
        for field in fieldmap:            
            for index, _ in enumerate(field):
                if index == 0:
                    fm_field = f'{field[string_fields[index]]}'
                elif index == 1:
                    fm_field = fm_field + f' "{field[string_fields[index]]}"'
                elif index in range(2,9):
                    fm_field = fm_field + f' {str(field[string_fields[index]])}'
                elif index == 10:
                    if field[string_fields[index]] in [None,'#']:
                        fm_field = fm_field + ',#'
                    else:
                        fm_field = fm_field + f',"{str(field[string_fields[index]])}"'
                elif index in range(9,14):
                    fm_field = fm_field + f',{str(field[string_fields[index]])}'

            out_fm.append(fm_field)
        out_fm = ';'.join(out_fm)
        out_fm = out_fm.replace('True ','true ').replace('False ','false ')
    else:
        raise TypeError('fieldmap is an unsupported type.')
    
    return out_fm

    #Convert From List-Dict to String
    elif isinstance(fieldmap, list):
        for field in fieldmap:
            if field[string_fields[10]] is None:
                field[string_fields[10]] = '#'
            fm_field = f'''{field[string_fields[0]]} "{field[string_fields[1]]}" {str(field[string_fields[2]])} {str(field[string_fields[3]])} {str(field[string_fields[4]])} {field[string_fields[5]]} {field[string_fields[6]]} {field[string_fields[7]]} {field[string_fields[8]]},{field[string_fields[9]]},{field[string_fields[10]]},{field[string_fields[11]]},{field[string_fields[12]]},{field[string_fields[13]]},{field[string_fields[14]]}'''
            out_fm.append(fm_field)
        out_fm = ';'.join(out_fm)
        out_fm = out_fm.replace(' True ',' true ').replace(' False ',' false ')
    else:
        raise TypeError('fieldmap is an unsupported type.')
    
    return out_fm
