
from psycopg2 import Error
from connection import connect_to_db
import pandas as pd
import datetime
from summary import create_bundle_pdf


def store_batch_controlbundle_data(db_name, controlbundle_data):
    """
    Performs batch insertion for control bundle OMR data.
    Establishes, commits, and closes its own database connection.
    """
    if not controlbundle_data:
        print("No control bundle data to insert.")
        return 

    conn = None
    cur = None
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()

        insert_bundle_query = """INSERT INTO bundleinfo(bundle_number, number_of_scripts, grand_total_marks, image_path, batchcode)
                                 VALUES (%s, %s, %s, %s, %s);"""
        insert_error_bundle_query = """INSERT INTO errorbundleinfo(image_path, bundle_number, number_of_scripts, grand_total_marks, batchcode)
                                       VALUES (%s, %s, %s, %s, %s);"""

        data_for_bundleinfo = []
        data_for_errorbundleinfo = []

        for bundlebarcode, numberofscripts, grandtotal, filename, file_path, batchcode in controlbundle_data:
            if grandtotal != -1 and numberofscripts != -1:
                data_for_bundleinfo.append((int(bundlebarcode), numberofscripts, grandtotal, file_path, batchcode))
            else:
                data_for_errorbundleinfo.append((file_path, int(bundlebarcode), numberofscripts, grandtotal, batchcode))

        if data_for_bundleinfo:
            cur.executemany(insert_bundle_query, data_for_bundleinfo)
            print(f"Inserted {len(data_for_bundleinfo)} records into bundleinfo.")
        if data_for_errorbundleinfo:
            cur.executemany(insert_error_bundle_query, data_for_errorbundleinfo)
            print(f"Inserted {len(data_for_errorbundleinfo)} records into errorbundleinfo.")
        
        conn.commit()
        print("Control bundle data committed successfully.")

    except Exception as e:
        print(f"Error in batch insertion for control bundles: {e}")
        if conn:
            conn.rollback() # Rollback on error
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("Control bundle database connection closed.")


def store_batch_mismatchbundle_data(db_name, mismatchbundle_data):
    """
    Performs batch insertion for mismatch bundle data.
    Establishes, commits, and closes its own database connection.
    """
    if not mismatchbundle_data:
        print("No mismatch bundle data to insert.")
        return 

    conn = None
    cur = None
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()

        insert_query = """INSERT INTO mismatchcontrolbundleinfo(image_path, bundle_number, number_of_scripts_as_per_bundle,
                                                                actual_number_of_scripts, grand_total_marks_as_per_bundle,
                                                                actual_grand_total_marks, batchcode, ignore)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"""
        
        data_to_insert = []
        for bundlebarcode, number_of_scripts_as_per_bundle, actual_number_of_scripts, \
            grand_total_marks_as_per_bundle, actual_grand_total_marks, filename, file_path, batchcode in mismatchbundle_data:
            data_to_insert.append((file_path, int(bundlebarcode), number_of_scripts_as_per_bundle, actual_number_of_scripts,
                                   grand_total_marks_as_per_bundle, actual_grand_total_marks, batchcode, False))

        if data_to_insert:
            cur.executemany(insert_query, data_to_insert)
            print(f"Inserted {len(data_to_insert)} records into mismatchcontrolbundleinfo.")
        
        conn.commit()
        print("Mismatch bundle data committed successfully.")

    except Exception as e:
        print(f"Error in batch insertion for mismatch bundles: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("Mismatch bundle database connection closed.")




def store_batch_script_data(db_name, script_data):
    """
    Performs batch insertion for script OMR data.
    Establishes, commits, and closes its own database connection.
    """
    if not script_data:
        print("No script data to insert.")
        return 

    conn = None
    cur = None
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()

        insert_script_query = """INSERT INTO scriptinfo(barcode, bundle_number, script_number, marks, image_path, batchcode)
                                 VALUES (%s, %s, %s, %s, %s, %s);"""
        insert_error_script_query = """INSERT INTO errorscriptinfo(image_path, barcode, bundle_number, script_number, marks, batchcode)
                                       VALUES (%s, %s, %s, %s, %s, %s);"""

        data_for_scriptinfo = []
        data_for_errorscriptinfo = []
        # script_data_to_insert.append((barcode, current_bundle_no, script_number, total_marks, name, image_file_path, batchcode))

        for barcode, bundlebarcode, scriptno, marks, filename, file_path, batchcode in script_data:
            bundle_num_for_db = int(bundlebarcode) if bundlebarcode is not None else -1

            if marks != -1 and scriptno != -1 and bundlebarcode is not None:
                data_for_scriptinfo.append((barcode, bundle_num_for_db, scriptno, marks, file_path, batchcode))
            else:
                data_for_errorscriptinfo.append((file_path, barcode, bundle_num_for_db, scriptno, marks, batchcode))

        if data_for_scriptinfo:
            cur.executemany(insert_script_query, data_for_scriptinfo)
            print(f"Inserted {len(data_for_scriptinfo)} records into scriptinfo.")
        if data_for_errorscriptinfo:
            cur.executemany(insert_error_script_query, data_for_errorscriptinfo)
            print(f"Inserted {len(data_for_errorscriptinfo)} records into errorscriptinfo.")
        
        conn.commit()
        print("Script data committed successfully.")

    except Exception as e:
        print(f"Error in batch insertion for script info: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("Script database connection closed.")


def storeinto_controlbundle_table(db_name, bundlebarcode,numberofscripts,grandtotal,filename,file_path,batchcode):
    try:
        connection = connect_to_db(db_name)    
        connection.autocommit = True
        cursor = connection.cursor()
        
        if grandtotal!=-1 and numberofscripts!=-1:
            insert_query = """INSERT INTO  bundleinfo(bundle_number, number_of_scripts, grand_total_marks,image_path,batchcode) 
                    VALUES (%s, %s, %s, %s,%s);"""
            # Execute the query with the respective Python variables
            cursor.execute(insert_query, (int(bundlebarcode),numberofscripts,grandtotal,file_path,batchcode))
        # Commit the transaction to save the data in the database
            connection.commit()
        else:
            insert_query = """INSERT INTO  errorbundleinfo(image_path, bundle_number,number_of_scripts, grand_total_marks,batchcode) 
                    VALUES (%s, %s, %s, %s,%s);"""
            # Execute the query with the respective Python variables
            cursor.execute(insert_query, (file_path,int(bundlebarcode),numberofscripts,grandtotal,batchcode))
            # Commit the transaction to save the data in the database
            connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except (Exception) as error:
        print("Error in store into control bundle while connecting to PostgreSQL", error)
        cursor.close()
        connection.close()

def storeinto_script_table(db_name, barcode,bundlebarcode,scriptno,marks,filename,file_path,batchcode):
    try:
        connection = connect_to_db(db_name)    
        connection.autocommit = True
        cursor = connection.cursor()
        if marks!=-1 and scriptno!=-1 and bundlebarcode is not None:
            insert_query = """INSERT INTO  scriptinfo(barcode, bundle_number, script_number, marks, image_path, batchcode) 
                    VALUES (%s, %s, %s, %s, %s, %s);"""
            # Execute the query with the respective Python variables
            cursor.execute(insert_query, (barcode,int(bundlebarcode),scriptno,marks,file_path,batchcode))
        # Commit the transaction to save the data in the database
            connection.commit()
        else:
            if bundlebarcode is None:
                bundlebarcode=-1
            insert_query = """INSERT INTO  errorscriptinfo(image_path, barcode,bundle_number, script_number, marks, batchcode) 
                    VALUES (%s, %s, %s, %s, %s, %s);"""
            # Execute the query with the respective Python variables
            cursor.execute(insert_query, (file_path,barcode,int(bundlebarcode),scriptno,marks,batchcode))
            # Commit the transaction to save the data in the database
            connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except (Exception) as error:
        print("Error in store into script while connecting to PostgreSQL", error)
        cursor.close()
        connection.close()

def storeinto_mismatchbundle_table(db_name, bundlebarcode,number_of_scripts_as_per_bundle, actual_number_of_scripts, grand_total_marks_as_per_bundle, actual_grand_total_marks,filename,file_path,batchcode):
    try:
        connection = connect_to_db(db_name)    
        connection.autocommit = True
        cursor = connection.cursor()
        insert_query = """INSERT INTO  mismatchcontrolbundleinfo(image_path, bundle_number,number_of_scripts_as_per_bundle, actual_number_of_scripts, grand_total_marks_as_per_bundle, actual_grand_total_marks,batchcode,ignore) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"""
            # Execute the query with the respective Python variables
        cursor.execute(insert_query, (file_path,int(bundlebarcode),number_of_scripts_as_per_bundle, actual_number_of_scripts, grand_total_marks_as_per_bundle, actual_grand_total_marks,batchcode,False))
            # Commit the transaction to save the data in the database
        connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

    except (Exception) as error:
        print("Error in mismatch bundle while connecting to PostgreSQL", error)
        cursor.close()
        connection.close()


def fetch_failed_bundle_info(db_name):
    """
    Fetches failed cases from the errorbundleinfo table.

    Args:
        conn (psycopg2.connection): An active database connection object.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a row
                    and contains 'image_path', 'bundle_number', 'number_of_scripts',
                    and 'grand_total_marks'. Returns an empty list on error.
    """
    failed_cases = []
    try:
        conn = connect_to_db(db_name)
        cursor = conn.cursor()
        # Ensure column names match the keys expected by your GUI
        query = """
        SELECT image_path, bundle_number, number_of_scripts, grand_total_marks,batchcode
        FROM errorbundleinfo;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        for row in rows:
            failed_cases.append(dict(zip(column_names, row)))
        cursor.close()
        print(f"Fetched {len(failed_cases)} failed bundle info cases.")
    except Error as e:
        print(f"Error fetching data from errorbundleinfo: {e}")
    finally:
        conn.close()
    return failed_cases

def fetch_failed_script_info(db_name):
    """
    Fetches failed cases from the errorscriptinfo table.

    Args:
        conn (psycopg2.connection): An active database connection object.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a row
                    and contains 'image_path', 'barcode', 'bundle_number',
                    'script_number', and 'marks'. Returns an empty list on error.
    """
    failed_cases = []

    try:
        conn = connect_to_db(db_name)
        cursor = conn.cursor()
        # Ensure column names match the keys expected by your GUI
        query = """
        SELECT image_path, barcode, bundle_number, script_number, marks, batchcode
        FROM errorscriptinfo;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        for row in rows:
            failed_cases.append(dict(zip(column_names, row)))
        cursor.close()
        conn.close()
        print(f"Fetched {len(failed_cases)} failed script info cases.")
    except Error as e:
        print(f"Error fetching data from errorscriptinfo: {e}")
    finally:
        conn.close()
    return failed_cases


def insert_verified_data_to_db(db_name, verified_data_list, omr_type):
    """
    Inserts a list of verified data dictionaries into the appropriate PostgreSQL table.
    Connects to the DB, inserts, then closes the connection.
    """
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()

        if omr_type == "control_bundle_info":
            insert_sql = """
                INSERT INTO bundleinfo(bundle_number, number_of_scripts, grand_total_marks,image_path,batchcode) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (bundle_number) DO UPDATE
                SET number_of_scripts = EXCLUDED.number_of_scripts,
                    grand_total_marks = EXCLUDED.grand_total_marks,
                    image_path = EXCLUDED.image_path,
                    batchcode = EXCLUDED.batchcode
            """
            delete_sql = """ DELETE FROM errorbundleinfo WHERE image_path = %s """
            
            for data in verified_data_list:
                try:
                    bundle_number = data.get('bundle_number')
                    num_scripts = int(data.get('number_of_scripts')) if data.get('number_of_scripts') else None
                    total_marks = float(data.get('grand_total_marks')) if data.get('grand_total_marks') else None
                    image_path = data.get('image_path')
                    batchcode = data.get('batchcode')
                    cur.execute(insert_sql, (bundle_number, num_scripts, total_marks, image_path, batchcode))
                    cur.execute(delete_sql, (image_path,))
                    print(f"Stored bundle_info for bundle_number: {bundle_number}")
                except (ValueError, TypeError) as e:
                    print(f"Error converting data for bundle_info: {data}. Error: {e}")
                except Exception as e:
                    print(f"Database error inserting bundle_info data: {data}. Error: {e}")
                    

        elif omr_type == "script_info":
            insert_sql = """
                INSERT INTO scriptinfo(barcode, bundle_number, script_number, marks, image_path, batchcode)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (barcode) DO UPDATE
                SET bundle_number = EXCLUDED.bundle_number,
                    marks = EXCLUDED.marks,
                    script_number = EXCLUDED.script_number,
                    image_path = EXCLUDED.image_path,
                    batchcode = EXCLUDED.batchcode
            """
            delete_sql = """ DELETE FROM errorscriptinfo WHERE image_path = %s """
            for data in verified_data_list:
                try:
                    barcode = data.get('barcode')
                    bundle_number = data.get('bundle_number')
                    marks = data.get('marks')
                    script_number = data.get('script_number')
                    image_path = data.get('image_path')
                    batchcode = data.get('batchcode')
                    cur.execute(insert_sql, (barcode, bundle_number,script_number, marks, image_path, batchcode))
                    cur.execute(delete_sql, (image_path,))
                    print(f"Stored script_info for barcode: {barcode}")
                except (ValueError, TypeError) as e:
                    print(f"Error converting data for script_info: {data}. Error: {e}")
                except Exception as e:
                    print(f"Database error inserting script_info data: {data}. Error: {e}")
                            
        conn.commit()
        cur.close()
        conn.close()
        return True # Success
    except Exception as error:
        print(f"An unexpected error occurred during database insertion: {error}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close() # Always close the connection


def identify_mismatch_control_bundle_info(db_name):
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        outf  = open(f"mismatch_control_bundle_info{today}.txt", "w")
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        #get value from bundleinfo table with same bundle number and update number_of_scripts_as_per_bundle
        update_sql = """
        UPDATE mismatchcontrolbundleinfo
        SET number_of_scripts_as_per_bundle = (
            SELECT number_of_scripts
            FROM bundleinfo
            WHERE mismatchcontrolbundleinfo.bundle_number = bundleinfo.bundle_number
        )
        """
        cur.execute(update_sql)
        conn.commit()
        #update grand total marks by taking total from bundleinfo table
        update_sql = """
        UPDATE mismatchcontrolbundleinfo
        SET grand_total_marks_as_per_bundle = (
            SELECT grand_total_marks
            FROM bundleinfo
            WHERE mismatchcontrolbundleinfo.bundle_number = bundleinfo.bundle_number
        )
        """
        cur.execute(update_sql)
        conn.commit()

        # update actual_grand_total_marks by taking total from scriptinfo table
        update_sql = """
        UPDATE mismatchcontrolbundleinfo
        SET actual_grand_total_marks = (
            SELECT SUM(marks)
            FROM scriptinfo
            WHERE mismatchcontrolbundleinfo.bundle_number = scriptinfo.bundle_number
        )
        """
        cur.execute(update_sql)
        conn.commit()
        # update actual_number_of_scripts by taking count from scriptinfo table
        update_sql = """
        UPDATE mismatchcontrolbundleinfo
        SET actual_number_of_scripts = (
            SELECT COUNT(*)
            FROM scriptinfo
            WHERE mismatchcontrolbundleinfo.bundle_number = scriptinfo.bundle_number
        )
        """
        cur.execute(update_sql)
        conn.commit()
        delete_sql = """
        DELETE FROM mismatchcontrolbundleinfo
        WHERE number_of_scripts_as_per_bundle = actual_number_of_scripts
        AND grand_total_marks_as_per_bundle = actual_grand_total_marks
        """
        cur.execute(delete_sql)
        conn.commit()
        #select mismatchcontrolbundleinfo table where number_of_scripts_as_per_bundle != actual_number_of_scripts
        select_sql = """
        SELECT * FROM mismatchcontrolbundleinfo where
        (number_of_scripts_as_per_bundle != actual_number_of_scripts
        OR grand_total_marks_as_per_bundle != actual_grand_total_marks) and ignore = false
        """
        cur.execute(select_sql)
        mismatched_bundle_info_list = cur.fetchall()
        for mismatched_bundle_info in mismatched_bundle_info_list:
            outf.write(str(mismatched_bundle_info) + "\n")
        outf.close()
        cur.close()
        conn.close()
        return len(mismatched_bundle_info_list) # Success
    except Exception as error:
        print(f"An unexpected error occurred during database insertion: {error}")
        return -1


# write script info into an excel file with headers
#Batch	Bundrc	Barcode	ToTmarks	AnsBkSlno	Papset	imgFileName	cnt_bndlno
# where cnt_bndlno is bundle_number, imagFileName is image_path, AnsBkSlno is script_number
# ToTmarks is marks, Barcode is barcode, Bundrc is "AAAA", Batch is "BBBB", Papset is 1
# use pandas to write to excel
def export_data_from_database(db_name):
    try:
        conn = connect_to_db(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT batchcode, 'AAAA', 'BBBB', barcode, marks, script_number, 1, image_path, bundle_number FROM scriptinfo order by bundle_number, script_number")
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=['Batch', 'Bundrc', 'Barcode', 'ToTmarks', 'AnsBkSlno', 'Papset', 'imgFileName', 'cnt_bndlno'])
        # file name must use db_name and today date
        today = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        df.to_excel(f'{db_name}_{today}.xlsx', index=False)
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error fetching data from bundleinfo: {e}")
    finally:
        conn.close()

# write bundle info into pdf
# get bundle_number,number_of_scripts from bundleinfo table
# write into pdf
def write_summary(db_name):
    try:
        conn = connect_to_db(db_name)
        cursor = conn.cursor()
        select_query = """
        SELECT bundle_number, number_of_scripts FROM bundleinfo order by bundle_number
        """
        cursor.execute(select_query)
        rows = cursor.fetchall()
        today = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        create_bundle_pdf(rows, f"bundle_report_{today}.pdf")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error fetching data from bundleinfo: {e}")
    finally:
        conn.close()


def check_and_correct_mismatches_in_scriptnumber(db_name):
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        out = open(f"mismatched_script_info{today}.txt", "w")
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        select_sql = """
        select s1.image_path, s1.barcode,s1.bundle_number,s1.script_number,s1.marks,s1.batchcode from scriptinfo s1,scriptinfo s2 
        where s1.bundle_number = s2.bundle_number and s1.script_number = s2.script_number 
        and s1.barcode != s2.barcode
        """
        cur.execute(select_sql)
        mismatched_script_info_list = cur.fetchall()
        
        for mismatched_script_info in mismatched_script_info_list:
            s1_image_path = mismatched_script_info[0]
            s1_barcode = mismatched_script_info[1]
            s1_bundle_number = mismatched_script_info[2]
            s1_script_number = mismatched_script_info[3]
            s1_marks = mismatched_script_info[4]
            s1_batchcode = mismatched_script_info[5]
            print(f"mismatched_script_info: {s1_image_path} {s1_barcode} {s1_bundle_number} {s1_marks} {s1_batchcode}", file=out)
            #insert bundleinfo into errorbundleinfo table
            insert_sql = """
            INSERT INTO errorscriptinfo(image_path, barcode,bundle_number, script_number, marks, batchcode)
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (image_path) DO NOTHING
            """
            cur.execute(insert_sql, (s1_image_path, s1_barcode, s1_bundle_number,-1, -1,s1_batchcode))
            #delete from scriptinfo table
            delete_sql = """
            DELETE FROM scriptinfo WHERE barcode = %s
            """
            cur.execute(delete_sql, (s1_barcode,))
            
        #update errorscriptinfo script_number to -1 
        # if the same script_number exists in scriptinfo table with same bundle_number
        
        select_sql = """
        select s1.image_path, s1.barcode,s1.bundle_number,s1.script_number,s1.marks, s2.image_path,s1.batchcode
        from scriptinfo s1, errorscriptinfo s2 
        where s1.bundle_number = s2.bundle_number and s1.script_number = s2.script_number
        and s1.barcode != s2.barcode"""
        cur.execute(select_sql)
        mismatched_script_info_list = cur.fetchall()
        for mismatched_script_info in mismatched_script_info_list:
            s1_image_path = mismatched_script_info[0]
            s1_barcode = mismatched_script_info[1]
            s1_bundle_number = mismatched_script_info[2]
            s1_script_number = mismatched_script_info[3]
            s1_marks = mismatched_script_info[4]
            s1_batchcode = mismatched_script_info[5]
            print(f"mismatched_script_info: {s1_image_path} {s1_barcode} {s1_bundle_number} {s1_marks} {s1_batchcode}", file=out)
            #insert bundleinfo into errorbundleinfo table
            insert_sql = """
            INSERT INTO errorscriptinfo(image_path, barcode,bundle_number, script_number, marks, batchcode)
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (image_path) DO NOTHING
            """
            cur.execute(insert_sql, (s1_image_path, s1_barcode, s1_bundle_number,-1, -1,s1_batchcode))
            #delete from scriptinfo table
            delete_sql = """
            DELETE FROM scriptinfo WHERE barcode = %s
            """
            cur.execute(delete_sql, (s1_barcode,))
            #update errorscriptinfo script_number, marks to -1 for a given image_path
            s2_image_path = mismatched_script_info[5]
            update_sql = """
            update errorscriptinfo 
            set script_number = -1, marks = -1
            where image_path = %s
            """
            cur.execute(update_sql, (s2_image_path,))

        #if errorscriptinfo has same script_number and bundle_number
        # if the same script_number exists in errorscriptinfo table with same bundle_number
        select_sql = """
        select s1.image_path, s1.barcode,s1.bundle_number,s1.script_number,s1.marks,s1.batchcode
        from errorscriptinfo s1, errorscriptinfo s2 
        where s1.bundle_number = s2.bundle_number and s1.script_number = s2.script_number and s1.script_number != -1 
        and s1.barcode != s2.barcode
        """
        cur.execute(select_sql)
        mismatched_script_info_list = cur.fetchall()
        for mismatched_script_info in mismatched_script_info_list:
            s1_image_path = mismatched_script_info[0]
            s1_barcode = mismatched_script_info[1]
            s1_bundle_number = mismatched_script_info[2]
            s1_script_number = mismatched_script_info[3]
            s1_marks = mismatched_script_info[4]
            s1_batchcode = mismatched_script_info[5]
            #insert bundleinfo into errorbundleinfo table
            print(f"mismatched_script_info: {s1_image_path} {s1_barcode} {s1_bundle_number} {s1_script_number} {s1_marks} {s1_batchcode}", file=out)
            #update errorscriptinfo script_number, marks to -1 for a given image_path
            update_sql = """
            update errorscriptinfo 
            set script_number = -1, marks = -1
            where image_path = %s
            """
            cur.execute(update_sql, (s1_image_path,))

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as error:
        print(f"An unexpected error occurred during database insertion: {error}")
        return False
    
def insert_into_labprintomrentryinfo(db_name, barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code):
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        insert_sql = """
        INSERT INTO labprintomrentryinfo(barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code)
        VALUES (%s, %s, %s, %s)
        """
        cur.execute(insert_sql, (barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as error:
        print(f"An unexpected error occurred during database insertion into labprintomrentryinfo: {error}")


def insert_into_labprintomrinfo(db_name, barcode, college_code, college_name, subject_code, number_of_lab_entries):
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        insert_sql = """
        INSERT INTO labprintomrinfo(barcode, college_code, college_name, subject_code, number_of_lab_entries)
        VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(insert_sql, (barcode, college_code, college_name, subject_code, number_of_lab_entries))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as error:
        print(f"An unexpected error occurred during database insertion into labprintomrinfo: {error}")

def get_number_of_lab_entries_all(db_name):
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        select_sql = """
        SELECT barcode,number_of_lab_entries FROM labprintomrinfo 
        """
        cur.execute(select_sql, ())
        number_of_lab_entries = cur.fetchall()
        cur.close()
        conn.close()
        return number_of_lab_entries if number_of_lab_entries else None
    except Exception as error:
        print(f"An unexpected error occurred during database insertion into labprintomrinfo: {error}")
        return None
    
def get_subject_code_all(db_name):
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        select_sql = """
        SELECT barcode,subject_code FROM labprintomrinfo 
        """
        cur.execute(select_sql, ())
        barsubjectcode = cur.fetchall()
        cur.close()
        conn.close()
        return barsubjectcode
    except Exception as error:
        print(f"An unexpected error occurred during database insertion into labprintomrinfo: {error}")
        return None

def insert_batch_labprintomrentryinfo(db_name, labprintomrentryinfo_data):
    """
    Performs a batch insert into the labprintomrentryinfo table.

    Args:
        cur (psycopg2.cursor): The database cursor.
        labprintomrentryinfo_data (list): A list of tuples, each representing a row.
    """
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        if labprintomrentryinfo_data:
            insert_sql_entryinfo = """
        INSERT INTO labprintomrentryinfo(barcode, hall_ticket_sno_in_omr, hall_ticket_number, subject_code)
        VALUES (%s, %s, %s, %s)
        """
            cur.executemany(insert_sql_entryinfo, labprintomrentryinfo_data)
            conn.commit()
            cur.close()
            conn.close()
            print("Batch insertion into labprintomrentryinfo completed.")
    except Exception as e:
            print(f"Error inserting into labprintomrentryinfo: {e}")

def insert_batch_labprintomrinfo(db_name,labprintomrinfo_data):
    """
    Performs a batch insert into the labprintomrinfo table.

    Args:
        cur (psycopg2.cursor): The database cursor.
        labprintomrinfo_data (list): A list of tuples, each representing a row.
    """
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()

        if labprintomrinfo_data:
            insert_sql_omrinfo = """
        INSERT INTO labprintomrinfo(barcode, college_code, college_name, subject_code, number_of_lab_entries)
        VALUES (%s, %s, %s, %s, %s)
        """
            cur.executemany(insert_sql_omrinfo, labprintomrinfo_data)
            conn.commit()
            cur.close()
            conn.close()
            print("Batch insertion into labprintomrinfo completed.")
    except Exception as e:
            print(f"Error inserting into labprintomrinfo: {e}")
            raise # Re-raise to allow the main function to handle rollback
    

def store_batch_lab_data(db_name,batchcode,lab_data_to_insert):
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        select_sql = """
        SELECT barcode,subject_code,number_of_lab_entries FROM labprintomrinfo 
        """
        cur.execute(select_sql, ())
        barsubjectcode = cur.fetchall()
        barcode_to_subjectcode = {}
        barcode_to_number_of_lab_entries = {}
        for bar,sub,num in barsubjectcode:
            barcode_to_subjectcode[bar] = sub
            barcode_to_number_of_lab_entries[bar] = num
        select_sql = """
            select barcode, hall_ticket_sno_in_omr, hall_ticket_number from labprintomrentryinfo
            order by barcode, hall_ticket_sno_in_omr
        """
        cur.execute(select_sql,())
        labprintomrentryinfo = cur.fetchall()
        barcode_to_hall_ticket_list = {}
        for bar, hall_ticket_sno_in_omr, hall_ticket_number in labprintomrentryinfo:
            if bar not in barcode_to_hall_ticket_list:
                barcode_to_hall_ticket_list[bar] = [hall_ticket_number]
            else:
                barcode_to_hall_ticket_list[bar].append(hall_ticket_number)


        labomr = []
        errorlabomr = []
        labentry = []
        errorlabentry = []
        for (barcode_image_file, barcode, total_marks, marks_of_students) in lab_data_to_insert:
            subject_code = barcode_to_subjectcode[barcode]
            num_entries = barcode_to_number_of_lab_entries[barcode]
            if total_marks == -1:
                errorlabomr.append((barcode_image_file, barcode,subject_code,batchcode,num_entries,total_marks))
            else:
                labomr.append((barcode,subject_code,batchcode,barcode_to_number_of_lab_entries[barcode],total_marks,barcode_image_file))
            for student_entry in marks_of_students:
                index =0
                for marks,image_path in student_entry:
                    if marks == -1:
                        errorlabentry.append((image_path,batchcode,barcode,subject_code,index+1,barcode_to_hall_ticket_list[barcode][index],marks))
                    else:
                        labentry.append((image_path,batchcode,barcode,subject_code,index+1,barcode_to_hall_ticket_list[barcode][index],marks))
                    index+=1
            
        # batch insert into labomrinfo table
        if labomr:
            insert_sql_omrinfo = """
            INSERT INTO labomrinfo(barcode, subject_code, batchcode, number_of_lab_entries, total_marks, image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_sql_omrinfo, labomr)
            conn.commit()
        if errorlabomr:
            insert_sql_omrinfo = """
            INSERT INTO errorlabomrinfo(image_path, barcode, subject_code, batchcode, number_of_lab_entries, total_marks)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_sql_omrinfo, errorlabomr)
            conn.commit()

        # batch insert into labentryinfo table
        if labentry:
            insert_sql_entryinfo = """
            INSERT INTO labentryinfo(image_path, batchcode, barcode, subject_code, hall_ticket_sno_in_omr, hall_ticket_number, marks)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_sql_entryinfo, labentry)
            conn.commit()
        if errorlabentry:
            insert_sql_entryinfo = """
            INSERT INTO errorlabentryinfo(image_path, batchcode, barcode, subject_code, hall_ticket_sno_in_omr, hall_ticket_number, marks)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_sql_entryinfo, errorlabentry)
            conn.commit()

        cur.close()
        conn.close()
        print("Batch insertion into labomrinfo and labentryinfo completed.")
    except Exception as e:
        print(f"Error inserting into labprintomrinfo: {e}")