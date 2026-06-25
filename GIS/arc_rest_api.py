"""
Tools for accessing  and utilizing ArcGIS REST API services, and 
"""

import requests

def list_rest_services(endpoint: str, return_type: str = 'Layer', timeout: int = 15, token: str = None) -> list:
    """
    Lists layers/tables, services, or folders contained in an ArcGIS REST API service.

    Params:
    * `endpoint`: An ArcGIS REST API endpoint.
    * `return_type`: Type of information to return.
        * Default: `'Layer'`
        * Accepted Values: `'Layer'`, `'Folder'`, `'Service'`, `'Error'`
    * `timeout`: Amount of seconds to wait for a timeout error.
        * Default: `15`
    * `token`: Token string to use when accessing the rest service. This creates a bearer token as a header.
        * Default: `None`
    """
    
    #Validate
    if return_type not in ['Layer','Folder','Service','Error']:
        raise ValueError('return_type is an invalid value.')
    if token is not None:
        token = {'Authorization': f'Bearer {token}'}
    if endpoint[-1] == '/':
        endpoint = endpoint.rstrip('/')

    #Get Services
    services = []
    folders = ['']
    for folder in folders:
        response = requests.get(f'{endpoint}/{folder}?f=json', timeout = timeout, headers = token).json()
        if 'error' in response:
            continue

        for service in response['services']:
            services.append(service)
        if 'folders' in response:
            for f in response['folders']:
                if folder != '':
                    folders.append(f'{folder}/{f}')
                else:
                    folders.append(f)
                
    #Return
    if return_type == 'Folder':
        folders.pop(0)
        return folders
    elif return_type == 'Service':
        return services
    
    #Get Individual Layers & Tables
    tbl_lyrs = []
    errors = []
    for service in services:
        try:
            response = requests.get(f"{endpoint}/{service['name']}/{service['type']}?f=json", timeout = timeout, headers = token).json()
        except requests.JSONDecodeError:
            errors.append(f"{endpoint}/{service['name']}/{service['type']}")
            continue
        if 'error' in response:
            errors.append(f"{endpoint}/{service['name']}/{service['type']}")
            continue
        
        if service['type'] in ['MapServer', 'FeatureServer']:
            for itype in ['layers','table']:
                if itype in response:
                    for item in response[itype]:
                        if 'type' in item:
                            item_type = item['type']
                        elif itype == 'table':
                            item_type = 'Table'
                        else:
                            item_type = None
                        tbl_lyrs.append({'name':item['name'], 'type':item_type, 'serviceType':service['type'], 
                            'url':f"{endpoint}/{service['name']}/{service['type']}/{item['id']}"})
        
        elif service['type'] == 'GPServer' and 'tasks' in response:
            for task in response['tasks']:
                tbl_lyrs.append({'name':task, 'type':'GeoprocessingTask', 'serviceType':service['type'], 'url':f"{endpoint}/{service['name']}/{service['type']}/{task.replace(' ','%20')}"})
        
        elif service['type'] in ['GeometryServer','VectorTileServer', 'GeocodeServer','ImageServer','SymbolServer']:
            if 'type' in response:
                item_type = response['type']
            else:
                item_type = None
            if 'name' in response:
                item_name = response['name']
            else:
                item_name = None
            tbl_lyrs.append({'name':item_name, 'type':item_type, 'serviceType':service['type'], 'url':f"{endpoint}/{service['name']}/{service['type']}"})
        
        elif service['type'] == 'NAServer':
            for itype in ['routeLayers','serviceAreaLayers','closestFacilityLayers','odCostMatrixLayers']:
                if itype in response:
                    for item in response[itype]:
                        tbl_lyrs.append({'name':item, 'type':itype, 'serviceType':service['type'], 
                            'url':f"{endpoint}/{service['name']}/{service['type']}/{item}"})
        else:
            raise KeyError(f'''Service type "{service['type']}" cannot be properly dealt with.''')

    #Return    
    if return_type == 'Error':
        return errors
    else:
        return tbl_lyrs

def rest_schema_compare(layer1: str, layer2: str, schema_fields: list or str = ['name','type','alias','domain'], ignore_geom: bool = False, token: str or None = None) -> bool:
    """
    Compares the schema of two ArcGIS REST layers or tables. 
    Returns `True` if the schema's match and `False` if not.
    
    Params:
    * `layer1`: URL to first layer or table to compare.
    * `layer2`: URL to second layer or table to compare.
    * `schema_fields`: The schema field(s) to use for match validation.
        * Default: `["name","type","alias","domain"]`
        * Accepted Values: `"name"`, `"type"`, `"alias"`, `"domain"`
    * `ignore_geom`: Whether to ignore geometry fields (SHAPE and esriFieldTypeGeometry).
    Removing these fields will allow map and feature service layers to return 
    `True` if they have the same base data.
        * Default: `False`
    * `token`: Token string to use when accessing the rest service. This creates a bearer token as a header.
        * Default: `None`
    """
    
    if token is not None:
        token = {'Authorization': f'Bearer {token}'}
    if isinstance(schema_fields, str):
        [schema_fields] = schema_fields
    for field in schema_fields:
        if field not in schema_fields:
            raise ValueError(f'Field "{field}" is not a valid schema field.')
    
    l1_json = requests.get(layer1 + '?f=json', timeout = 15, headers = token).json()
    l2_json = requests.get(layer2 + '?f=json', timeout = 15, headers = token).json()
    
    for field in schema_fields:
        l1_fields = {f[field] for f in l1_json['fields']}
        l2_fields = {f[field] for f in l2_json['fields']}
        if ignore_geom is True:
            for value in ['SHAPE','esriFieldTypeGeometry']:
                if value in l1_fields:
                    l1_fields.remove(value)
                if value in l2_fields:
                    l2_fields.remove(value)
        if l1_fields != l2_fields:
            return False
    
    return True
