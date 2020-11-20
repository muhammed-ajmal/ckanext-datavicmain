import psycopg2
from psycopg2 import Error

try:
    """
    THE ISSUE:

    Between 15th & 16th Oct 2020 - VicRoads changed the GUID/Identifier of their records
    from an http:// to an https:// prefix

    This caused the CKAN harvester to create a new, duplicate, dataset in CKAN
    
    And the original dataset to be marked as "deleted"

    THE SOLUTION:

    - "Re-attach" the original package_id to the new GUID in the harvest_object table
    - Remove the duplicated datasets created by the harvester
    - Remove any harvest history of the new GUID to the duplicated package
    - Remove any harvest history of the old GUID to the original package_id
    - 
    """
    duplicate_packages_deleted = 0
    original_packages_reactivated = 0

    deleted_packages = []
    reactivated_packages = []

    connection = psycopg2.connect(user = "ckan",
                                  password = "ckan",
                                  host = "postgres",
                                  port = "5432",
                                  database = "ckan")

    # Ref.: https://stackoverflow.com/a/43634941/9012261
    connection.autocommit = True

    cursor = connection.cursor()

    # SELECT query
    query = '''
        SELECT ho1.id, 
            ho1.guid AS ho1_guid, 
            ho1."current", 
            ho1.package_id AS ho1_package_id,
            p.name AS ho1_name,
            ho2.ho2_count,
            ho2.package_id AS ho2_package_id,
            ho2.guid,
            p2."name" AS ho2_name,
            concat(\'UPDATE harvest_object SET package_id = \'\'\', ho2.package_id, \'\'\' WHERE id = \'\'\', ho1.id, \'\'\';')
        FROM harvest_object ho1
        JOIN package p ON p.id = ho1.package_id
        LEFT JOIN 
            (
                SELECT COUNT(id) AS ho2_count, guid, package_id
                FROM harvest_object
                WHERE "current" = FALSE
                AND package_id IS NOT NULL
                GROUP BY guid, package_id
            ) AS ho2
        ON ho2.guid = concat(\'http\', trim(\'https\' from ho1.guid))
            AND ho1.package_id <> ho2.package_id
        LEFT JOIN package p2 ON p2.id = ho2.package_id
        WHERE ho1.harvest_source_id = \'d073191f-ff10-44b2-9c0c-d632e0794787\'
            AND ho1.current = TRUE
        -- Only show those without a match
        --	AND ho2.package_id IS NULL
    '''
    cursor.execute(query)
    records = cursor.fetchall()

    from pprint import pprint

    for record in records:
        new_harvest_object_id = record[0]
        new_guid = record[1]
        current = record[2]
        new_package_id = record[3]
        new_package_name = record[4]

        old_package_id = record[6]
        old_guid = record[7]
        old_package_name = record[8]

        update_sql = record[9]

        if not old_package_id:
            continue

        print('--------------\n')
        print('ho1.id:         {}'.format(new_harvest_object_id))
        print('ho1_guid:       {}'.format(new_guid))
        print('current:        {}'.format(record[2]))
        print('ho1_package_id: {}'.format(record[3]))
        print('ho1_name:       {}'.format(record[4]))
        print('ho2_count:      {}'.format(record[5]))
        print('ho2_package_id: {}'.format(record[6]))
        print('ho2_guid:       {}'.format(old_guid))
        print('ho2_name:       {}'.format(record[8]))
        print('UPDATE:         {}\n'.format(update_sql))

        #continue

        # Attach new GUID to old package_id
        print('>>> Attaching new GUID to old package ID')
        cursor.execute(update_sql)
        count = cursor.rowcount
        print('>>> {} rows updated'.format(count))
        print('- - - - -')

        # Mark new package_id as deleted
        print('>>> Marking new package ID as deleted')
        cursor.execute("UPDATE package SET state = 'deleted' WHERE id = '{0}';".format(new_package_id))
        count = cursor.rowcount
        print('>>> {} rows updated'.format(count))
        duplicate_packages_deleted += 1
        deleted_packages.append(new_package_name)
        print('- - - - -')

        # Mark OLD package_id as active AND set `source` to new VicRoads JSON feed identifier
        print('>>> Marking OLD package ID as active AND updating source identifier')
        cursor.execute("UPDATE package SET state = 'active', url = '{0}' WHERE id = '{1}';".format(new_guid, old_package_id))
        count = cursor.rowcount
        print('>>> {} rows updated'.format(count))
        original_packages_reactivated += 1
        reactivated_packages.append(old_package_name)
        print('- - - - -')

        # NEED TO DELETE any harvest_object_extra records first...
        print('>>> Deleting any obsolete harvest_object_extra with the OLD GUID')
        sql = "DELETE FROM harvest_object_extra WHERE harvest_object_id IN (SELECT id FROM harvest_object WHERE guid = '{}');".format(old_guid)
        print('>>> {}'.format(sql))
        cursor.execute(sql)
        count = cursor.rowcount
        print('>>> {} rows deleted'.format(count))
        print('- - - - -')

        # AND NEED TO DELETE any harvest_object_error records first...
        print('>>> Deleting any obsolete harvest_object_error with the OLD GUID')
        cursor.execute("DELETE FROM harvest_object_error WHERE harvest_object_id IN (SELECT id FROM harvest_object WHERE guid = '{}');".format(old_guid))
        count = cursor.rowcount
        print('>>> {} rows deleted'.format(count))
        print('- - - - -')

        # DELETE all harvest_objects with the OLD GUID
        print('>>> Deleting all harvest_objects with the OLD GUID')
        cursor.execute("DELETE FROM harvest_object WHERE guid = '{0}';".format(old_guid))
        count = cursor.rowcount
        print('>>> {} rows deleted'.format(count))
        print('- - - - -')

        # DELETE any harvest objects where the NEW GUID is associated with the NEW package_id
        sql = '''
            DELETE FROM harvest_object_extra 
            WHERE harvest_object_id IN (
                SELECT id 
                FROM harvest_object 
                WHERE guid = '{0}' 
                    AND package_id = '{1}'
            );
        '''.format(new_guid, new_package_id)
        print('>>> {}'.format(sql))
        cursor.execute(sql)

        sql = '''
            DELETE FROM harvest_object_error 
            WHERE harvest_object_id IN (
                SELECT id 
                FROM harvest_object 
                WHERE guid = '{0}' 
                    AND package_id = '{1}'
            );
        '''.format(new_guid, new_package_id)
        print('>>> {}'.format(sql))
        cursor.execute(sql)

        print('>>> Deleting any harvest_objects with new GUID pointing to NEW package_id')
        sql = "DELETE FROM harvest_object WHERE guid = '{0}' AND package_id = '{1}';".format(new_guid, new_package_id)
        print('>>> {}'.format(sql))
        cursor.execute(sql)
        count = cursor.rowcount
        print('>>> {} rows deleted\n'.format(count))

except (Exception, psycopg2.DatabaseError) as error :
    print ("Error while creating PostgreSQL table", error)
finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

print('\nDuplicate packages deleted: {}\n'.format(duplicate_packages_deleted))
print('Original packages re-activated: {}\n'.format(original_packages_reactivated))
