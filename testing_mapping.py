import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, mapper, relationship
from sqlalchemy.orm import declarative_base
from xml.etree.ElementTree import parse

# Configure your database connection string here
mysqlcon = 'mysql+pymysql://ream_dba:(3d3n052$@192.168.49.130:3306/reamdb'
DATABASE_URI = mysqlcon

# Update this with the directory where the .orm.xml files are saved
ORM_XML_DIR = './xml_mapping'

# Set up SQLAlchemy base
Base = declarative_base()

# Define a function to convert CamelCase to snake_case
def camel_to_snake(name):
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# Parse the ORM XML files
def parse_orm_xml(file_path):
    tree = parse(file_path)
    root = tree.getroot()
    entity_mappings = {}
    for entity in root.findall('entity'):
        entity_name = entity.get('name')
        table_name = entity.get('table')
        fields = []
        for field in entity.findall('field'):
            field_name = field.get('name')
            field_type = field.get('type')
            fields.append((field_name, field_type))
        relationships = []
        for relation in entity.findall('many-to-one'):
            field = relation.get('field')
            target_entity = relation.get('target-entity')
            join_column = relation.find('join-column').get('name')
            referenced_column = relation.find('join-column').get('referenced-column-name')
            relationships.append((field, target_entity, join_column, referenced_column))
        entity_mappings[entity_name] = (table_name, fields, relationships)
    return entity_mappings

# Function to map entities using SQLAlchemy
def map_entities(engine, entity_mappings):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    for entity_name, (table_name, fields, relationships) in entity_mappings.items():
        columns = []
        table = metadata.tables[table_name]
        for field_name, field_type in fields:
            column = table.c[field_name]
            columns.append(column)
        mapper_dict = {col.name: col for col in columns}
        for field, target_entity, join_column, referenced_column in relationships:
            target_table = camel_to_snake(target_entity)
            target_col = metadata.tables[target_table].c[referenced_column]
            mapper_dict[field] = relationship(target_entity, primaryjoin=table.c[join_column] == target_col)
        orm_class = type(entity_name, (Base,), mapper_dict)
        mapper(orm_class, table)

# Connect to the database and validate mappings
def main():
    engine = create_engine(DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    entity_mappings = {}
    for file_name in os.listdir(ORM_XML_DIR):
        if file_name.endswith('.orm.xml'):
            file_path = os.path.join(ORM_XML_DIR, file_name)
            entity_mappings.update(parse_orm_xml(file_path))
    
    map_entities(engine, entity_mappings)
    
    # Perform a simple query to ensure mappings are correct
    for entity_name in entity_mappings:
        orm_class = Base._decl_class_registry.get(entity_name)
        if orm_class:
            try:
                session.query(orm_class).first()
                print(f"Mapping for {entity_name} is valid.")
            except Exception as e:
                print(f"Error validating mapping for {entity_name}: {e}")

if __name__ == "__main__":
    main()
