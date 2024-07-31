"""
Description: 
Converts a XML file to a (mostly) flattened table-like format.

Version: 1.0.0
Created: 07/30/2024
Created by: Tanner Hammond
Python Version: 3.11.8
"""

from lxml import etree

def xml_flatten(xml_file: str, max_depth: int = 10) -> list:
    """
    Converts an xml file to a listdict.

    Params:
    * `xml_file`: File path to XML file.
    * `max_depth`: Maximum depth (i.e., number of indentations) to do.
        * Default: `10`
    """

    #Get File Data
    xml_data = []
    tree = etree.parse(xml_file)
    root = tree.getroot()

    #Get Roots
    id_val = 1
    for node in root:
        xml_data.append({'id':id_val, 'element':node, 'tags':node.tag,'attributes':node.attrib, 'text': node.text, 'depth':0, 'parentId':'root', 'numChildren':len(node)})
        id_val += 1

    #Get Children
    depth = 1
    while depth <= max_depth and depth -1 == xml_data[-1]['depth']:
        for node in xml_data:
            if node['numChildren'] > 0 and node['depth'] == depth - 1:
                for child in node['element']:
                    xml_data.append({'id':id_val, 'element':child, 'tags':child.tag,'attributes':child.attrib, 'text': child.text, 'depth':depth, 'parentId':node['id'], 'numChildren':len(child)})
                    id_val += 1
        depth += 1
    
    #Clean Up
    for element in xml_data:
        #Get Attributes Data
        if element['attributes'] == []:
            element['attributes'] = None
        else:
            attributes = {}
            for attrib in element['attributes']:
                attributes[attrib] = element['element'].attrib[attrib]
            element['attributes'] = attributes

        #Replace Space Only Text with None
        try:
            if element['text'].replace('\n','').replace('\t','').replace(' ','') == '':
                element['text'] = None
        except:
            pass
        
        #Delete Element Tree Object
        del element['element']

    return xml_data


#Usage -----
xml_file = 'C:/path/to/file.xml'
depth_limit = 10
xml_table = xml_flatten(xml_file, depth_limit)