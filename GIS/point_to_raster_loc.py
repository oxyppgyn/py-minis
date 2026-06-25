"""
ArcGIS Pro implementation to get the raster cell (column + row number) a points fall within.
"""

def point_to_raster_loc(raster, point_layer, id_column):
    if arcpy.Describe(raster).spatialReference.name != arcpy.Describe(point_layer).spatialReference.name:
        raise Exception('Raster and point layer must be in the same coordinate system.')
    
    #Get Raster Extent + Info
    x_min = arcpy.Describe(raster).extent.XMin
    x_max = arcpy.Describe(raster).extent.XMax
    y_min = arcpy.Describe(raster).extent.YMin
    y_max = arcpy.Describe(raster).extent.YMax
    height = arcpy.Describe(raster).meanCellHeight
    width = arcpy.Describe(raster).meanCellWidth
    #column_num = int((x_max - x_min)/width)
    #row_num = int((y_max - y_min)/height)
    
    out_data = []
    with arcpy.da.SearchCursor(point_layer, ['SHAPE@',id_column]) as searchcursor:
        for row in searchcursor:
            id_val = row[1]
            
            point_x = row[0].trueCentroid.X
            point_y = row[0].trueCentroid.Y
            
            if point_x > x_max or point_x < x_min:
                raise Exception('Point is outside of raster area (X direction).')
            if point_y > y_max or point_y < y_min:
                raise Exception('Point is outside of raster area (Y direction).')
            
            column = int((point_x - x_min) / width)
            row = int((point_y - y_min) / height)
            
            out_data.append({id_column: id_val, 'Column': column, 'Row':row})
            
    return out_data