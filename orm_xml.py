#------------------------------------------------------------------------
#
#  Doctrine XML Entity Mapping Generator from SQL Script
#  Author: Rolando Cedeno 
#  Date: July 4, 2024
#
#------------------------------------------------------------------------

import re
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)

def extract_table_definitions(sql_script):
    table_definitions = {}
    current_table = None
    current_columns = []
    
    for line in sql_script.splitlines():
        line = line.strip()
        if line.startswith("CREATE TABLE"):
            if current_table:
               table_definitions[current_table] = current_columns

            current_table = re.findall(r'`(\w+)`', line)[0]
            current_columns = []

        elif line.startswith("`"):
             current_columns.append(line)
        elif line.startswith(");"):
             if current_table:
                table_definitions[current_table] = current_columns
                current_table = None
                current_columns = []
    
    return table_definitions

def extract_relationships(sql_script):
    foreign_key_pattern = re.compile(r'FOREIGN KEY \(`(\w+)`\) REFERENCES `(\w+)` \(`(\w+)`\)')
    relationships = foreign_key_pattern.findall(sql_script)
    relationship_mappings = []
    
    for fk_column, ref_table, ref_column in relationships:
        relationship_mappings.append({ 'foreign_key_column': fk_column, 'referenced_table': ref_table, 'referenced_column': ref_column  })
    
    return relationship_mappings

def generate_doctrine_mapping(table_definitions, relationships, output_dir):
    type_mappings = {
        'int':       'integer',
        'varchar':   'string',
        'char':      'string',
        'date':      'date',
        'datetime':  'datetime',
        'timestamp': 'datetime',
        'json':      'json',
        'bit':       'boolean'
    }
    
    xml_files = {}
    for table_name, columns in table_definitions.items():
        print(f"Generating XML for table: {table_name}")
        clean_table_name = table_name.replace("ream_", "")
        entity_name = to_camel_case(clean_table_name)
        
        entity = Element('doctrine-mapping')
        entity.set('xmlns', 'http://doctrine-project.org/schemas/orm/doctrine-mapping')
        entity.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        entity.set('xsi:schemaLocation', 'http://doctrine-project.org/schemas/orm/doctrine-mapping http://doctrine-project.org/schemas/orm/doctrine-mapping.xsd')
        
        entity_class = SubElement(entity, 'entity')
        entity_class.set('name', entity_name)
        entity_class.set('table', table_name)
        
        for column in columns:
            column_name = re.findall(r'`(\w+)`', column)[0]
            field = SubElement(entity_class, 'field')
            field.set('name', column_name)
            field.set('column', column_name)
            
            for key, value in type_mappings.items():
                if key in column:
                   field.set('type', value)
                   break
                
            if 'AUTO_INCREMENT' in column:
                field.set('id', 'true')
        
        for rel in relationships:
            if rel['referenced_table'] == table_name:
               association = SubElement(entity_class, 'many-to-one')
               association.set('field', rel['foreign_key_column'])
               association.set('target-entity', to_camel_case(rel['referenced_table'].replace("ream_", "")))
               join_column = SubElement(association, 'join-column')
               join_column.set('name', rel['foreign_key_column'])
               join_column.set('referenced-column-name', rel['referenced_column'])
        
        xml_str = parseString(tostring(entity)).toprettyxml(indent="   ")
        xml_files[f"{entity_name}.orm.xml"] = xml_str
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for file_name, xml_content in xml_files.items():
        with open(os.path.join(output_dir, file_name), 'w') as xml_file:
            xml_file.write(xml_content)
    
    print("Doctrine mapping XML files have been generated and saved.")

# Read the SQL script
file_path  = './entities_rev1.sql'   # Update this with the actual path to your SQL script file
output_dir = './xml_mapping'         # Update this with the desired output directory

with open(file_path, 'r') as file:
    sql_script = file.read()

# Extract table definitions and relationships
table_definitions = extract_table_definitions(sql_script)
relationships     = extract_relationships(sql_script)

# Generate Doctrine mapping XML files
generate_doctrine_mapping(table_definitions, relationships, output_dir)
