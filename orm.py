#------------------------------------------------------------------------
#
#  Entity Mapping and Repository Generator from SQL Script
#  Author: Rolando Cedeno 
#  Date: July 4, 2024
#
#------------------------------------------------------------------------
 
import os
import re

def map_sql_type(sql_type):
    type_mapping = {
        'int':      ('integer', 'int'),
        'varchar':  ('string', 'string'),
        'bit':      ('boolean', 'bool'),
        'date':     ('date', '\\DateTimeInterface'),
        'datetime': ('datetime', '\\DateTimeInterface'),
    }
    for key in type_mapping.keys():
        if key in sql_type:
            return type_mapping[key]
    return ('string', 'string')  # default type

def camel_case(input_str):
    components = input_str.split('_')
    return components[0].lower() + ''.join(x.title() for x in components[1:])

def pascal_case(input_str):
    return ''.join(word.capitalize() for word in input_str.split('_'))

def generate_getters_and_setters(columns):
    methods = ""
    for column in columns:
        if column['name'].startswith(('fk_', 'idx_')):  # Skip foreign key and index columns
            continue
        
        column_name = column['name']
        camel_column_name = camel_case(column_name)
        pascal_column_name = pascal_case(column_name)
        _, php_type = map_sql_type(column['type'])
        
        # Getter
        methods += f"    public function get{pascal_column_name}(): ?{php_type}\n    {{\n"
        methods += f"        return $this->{camel_column_name};\n    }}\n\n"
        
        # Setter
        methods += f"    public function set{pascal_column_name}(?{php_type} ${camel_column_name}): self\n    {{\n"
        methods += f"        $this->{camel_column_name} = ${camel_column_name};\n"
        methods += f"        return $this;\n    }}\n\n"
    
    return methods

def generate_entity_class(table_name, columns):
    class_name = pascal_case(table_name.replace('ream_', ''))
    entity_code = f"<?php\n\nnamespace App\Entity;\n\nuse Doctrine\ORM\Mapping as ORM;\n\n#[ORM\Entity(repositoryClass: 'App\\Repository\\{class_name}Repository')]\n#[ORM\Table(name: '{table_name}')]\nclass {class_name}\n{{\n"
    
    for column in columns:
        if column['name'].startswith(('fk_', 'idx_')):  # Skip foreign key and index columns
            continue

        column_name = column['name']
        camel_column_name = camel_case(column_name)
        doctrine_type, php_type = map_sql_type(column['type'])
        nullable = column['nullable']
        default  = column['default']

        if column_name == 'id':
            entity_code += f"    #[ORM\Id]\n    #[ORM\GeneratedValue]\n    #[ORM\Column(type: '{doctrine_type}')]\n    private int ${camel_column_name};\n\n"
        else:
            nullable_str = ', nullable: true' if nullable else ''
            default_str = f", default: '{default}'" if default else ''
            entity_code += f"    #[ORM\Column(name: '{column_name}', type: '{doctrine_type}'{nullable_str}{default_str})]\n    private ?{php_type} ${camel_column_name} = null;\n\n"

    entity_code += generate_getters_and_setters(columns)
    entity_code += "}\n"
    
    return entity_code

def generate_repository_class(table_name):
    class_name = pascal_case(table_name.replace('ream_', ''))
    repository_code = f"<?php\n\nnamespace App\Repository;\n\nuse App\Entity\\{class_name};\nuse Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;\nuse Doctrine\Persistence\ManagerRegistry;\n\n/**\n * @extends ServiceEntityRepository<{class_name}>\n */\nclass {class_name}Repository extends ServiceEntityRepository\n{{\n    public function __construct(ManagerRegistry $registry)\n    {{\n        parent::__construct($registry, {class_name}::class);\n    }}\n\n    //    /**\n    //     * @return {class_name}[] Returns an array of {class_name} objects\n    //     */\n    //    public function findByExampleField($value): array\n    //    {{\n    //        return $this->createQueryBuilder('r')\n    //            ->andWhere('r.exampleField = :val')\n    //            ->setParameter('val', $value)\n    //            ->orderBy('r.id', 'ASC')\n    //            ->setMaxResults(10)\n    //            ->getQuery()\n    //            ->getResult()\n    //        ;\n    //    }}\n\n    //    public function findOneBySomeField($value): ?{class_name}\n    //    {{\n    //        return $this->createQueryBuilder('r')\n    //            ->andWhere('r.exampleField = :val')\n    //            ->setParameter('val', $value)\n    //            ->getQuery()\n    //            ->getOneOrNullResult()\n    //        ;\n    //    }}\n}}\n"
    
    return repository_code

def parse_sql_file(file_path):
    with open(file_path, 'r') as file:
        sql_content = file.read()

    table_segments = sql_content.split('CREATE TABLE')

    table_structures = {}

    for segment in table_segments[1:]:
        table_name_match = re.search(r'`(?P<table_name>\w+)`', segment)
        table_name = table_name_match.group('table_name')
        
        columns_segment_match = re.search(r'\((?P<columns_segment>.+?)\)\sENGINE=', segment, re.DOTALL)
        columns_segment = columns_segment_match.group('columns_segment')
        
        column_definitions = columns_segment.split(',\n')
        
        columns = []
        
        for column_definition in column_definitions:
            column_match = re.search(r'`(?P<column_name>\w+)`\s+(?P<column_type>[\w\s\(\)]+)(?:\s+DEFAULT\s+(?P<default>[^,\n]+))?(?P<nullable>\sNOT NULL)?', column_definition.strip())
            
            if column_match:
                column_name = column_match.group('column_name')
                if column_name.startswith(('fk_', 'idx_')):  # Skip foreign key and index columns
                   continue
                column_type = map_sql_type(column_match.group('column_type').strip())
                nullable = column_match.group('nullable') is None
                default = column_match.group('default').strip("'") if column_match.group('default') else None

                columns.append({
                    'name':     column_name,
                    'type':     column_type[0],
                    'php_type': column_type[1],
                    'nullable': nullable,
                    'default':  default
                })

        table_structures[table_name] = columns

    return table_structures

def main():
    file_path = './entities_rev1.sql'
    table_structures = parse_sql_file(file_path)
    
    output_dir = 'entities'
    os.makedirs(output_dir, exist_ok=True)
    repository_dir = 'repositories'
    os.makedirs(repository_dir, exist_ok=True)

    for table_name, columns in table_structures.items():
        entity_code = generate_entity_class(table_name, columns)
        class_name = pascal_case(table_name.replace('ream_', ''))
        entity_file_path = os.path.join(output_dir, f"{class_name}.php")
        with open(entity_file_path, 'w') as entity_file:
            entity_file.write(entity_code)
        print(f"Generated entity for table: {table_name}")
        
        repository_code = generate_repository_class(table_name)
        repository_file_path = os.path.join(repository_dir, f"{class_name}Repository.php")
        with open(repository_file_path, 'w') as repository_file:
            repository_file.write(repository_code)
        print(f"Generated repository for table: {table_name}")

if __name__ == "__main__":
    main()
