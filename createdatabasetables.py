
from connection import connect_to_db



def create_database(db_name):
    try:
        conn = connect_to_db("postgres")
        cur = conn.cursor()
        #check if database already exists and create only if it not exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            conn = connect_to_db("postgres")
            conn.autocommit = True
            cur=conn.cursor()
            create_db_query = f"CREATE DATABASE {db_name}"
            cur.execute(create_db_query)
            #conn.commit()
            cur.close()
            conn.close()
            print(f"Database {db_name} created successfully.")
        else:
            cur.close()
            conn.close()
            print(f"Database {db_name} already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
        
def create_tables(db_name):
    commands = [
        """ CREATE TABLE IF NOT EXISTS scriptinfo (
        barcode VARCHAR(20) PRIMARY KEY,
        bundle_number bigint,
        script_number integer,
        marks integer,
        image_path VARCHAR(400),
        batchcode VARCHAR(20),
        CONSTRAINT con1 CHECK (script_number <= 40 AND marks <= 100 AND image_path <> '') );""",
        """ CREATE TABLE IF NOT EXISTS bundleinfo (
        bundle_number bigint PRIMARY KEY,
        number_of_scripts integer,
        grand_total_marks integer,
        image_path VARCHAR(400),
        batchcode VARCHAR(20),
        CONSTRAINT con2 CHECK (number_of_scripts <= 40 AND grand_total_marks <= 4000 AND image_path <> '') );""",
        """ CREATE TABLE IF NOT EXISTS errorscriptinfo (
        image_path VARCHAR(400) PRIMARY KEY,
        barcode VARCHAR(20),
        bundle_number bigint,
        script_number integer,
        marks integer,
        batchcode VARCHAR(20)        
        );
        """,
        """ CREATE TABLE IF NOT EXISTS errorbundleinfo (
        image_path VARCHAR(400) PRIMARY KEY,
        bundle_number bigint,
        number_of_scripts integer,
        grand_total_marks integer,
        batchcode VARCHAR(20)
        );""",
        """ CREATE TABLE IF NOT EXISTS mismatchcontrolbundleinfo (
        image_path VARCHAR(400) PRIMARY KEY,
        bundle_number bigint,
        number_of_scripts_as_per_bundle integer,
        actual_number_of_scripts integer,
        grand_total_marks_as_per_bundle integer,
        actual_grand_total_marks integer,
        batchcode VARCHAR(20),
        ignore boolean
        );"""
        ,
        """ CREATE TABLE IF NOT EXISTS mismatchscriptinfo (
        image_path VARCHAR(400) PRIMARY KEY,
        barcode VARCHAR(20),
        bundle_number bigint,
        script_number_as_per_bundle integer,
        actual_script_number integer,
        marks integer,
        batchcode VARCHAR(20)
        );"""
        ,
        """ CREATE TABLE IF NOT EXISTS doublentrybundleinfo (
        imagepath VARCHAR(400) PRIMARY KEY,
        bundleno_user1 bigint,
        numberofscripts_user1 integer,
        grandtotalmarks_user1 integer,
        bundleno_user2 bigint,
        numberofscripts_user2 integer,
        grandtotalmarks_user2 integer,
        batchcode VARCHAR(20),
        timestamp timestamp
        );""", 
        """ CREATE TABLE IF NOT EXISTS doublentryscriptinfo (
        imagepath VARCHAR(400) PRIMARY KEY,
        barcode_user1 VARCHAR(20),
        bundleno_user1 bigint,
        scriptno_user1 integer,
        marks_user1 integer,
        barcode_user2 VARCHAR(20),
        bundleno_user2 bigint,
        scriptno_user2 integer,
        marks_user2 integer,
        batchcode VARCHAR(20),
        timestamp timestamp
        );""",    
        """ create table if not exists labprintomrinfo(
            barcode VARCHAR(20) PRIMARY KEY,
            college_code VARCHAR(20),
            college_name VARCHAR(100),
            subject_code VARCHAR(20),
            number_of_lab_entries integer
        )
        """,
        """ create table if not exists labprintomrentryinfo(
           barcode VARCHAR(20),
           hall_ticket_sno_in_omr integer,
           hall_ticket_number VARCHAR(20),
           subject_code VARCHAR(20),
           unique(hall_ticket_number,subject_code)
        )"""
        ,
        """ CREATE TABLE IF NOT EXISTS labomrinfo (
        barcode VARCHAR(20) PRIMARY KEY,
        subject_code VARCHAR(20),
        batchcode VARCHAR(20),
        number_of_lab_entries integer,
        grand_total_marks integer,
        imagepath VARCHAR(400)
        );""",
        """ CREATE TABLE IF NOT EXISTS errorlabomrinfo (
        imagepath VARCHAR(400) PRIMARY KEY,
        barcode VARCHAR(20),
        subject_code VARCHAR(20),
        batchcode VARCHAR(20),
        number_of_lab_entries integer,
        grand_total_marks integer
        );""" ,
        
        """create table if not exists labinfo(
            imagepath VARCHAR(400),
            batchcode VARCHAR(20),
            barcode VARCHAR(20),
            subject_code VARCHAR(20),
            hall_ticket_sno_in_omr integer,
            hall_ticket_number VARCHAR(20),
            marks integer,
            unique(hall_ticket_number,subject_code)
        )
        """,
        """ create table if not exists errorlabinfo(
            imagepath VARCHAR(400),
            batchcode VARCHAR(20),
            barcode VARCHAR(20),
            subject_code VARCHAR(20),
            hall_ticket_sno_in_omr integer,
            hall_ticket_number VARCHAR(20),
            marks integer,
            unique(imagepath,hall_ticket_sno_in_omr)   
        )
       """,
       """create table if not exists doubleentrylabinfo(
       imagepath VARCHAR(400),
       batchcode VARCHAR(20),
       barcode_user1 VARCHAR(20),
       subject_code_user1 VARCHAR(20),
       hall_ticket_sno_in_omr_user1 integer,
       hall_ticket_number_user1 VARCHAR(20),
       marks_user1 integer,
       barcode_user2 VARCHAR(20),
       subject_code_user2 VARCHAR(20),
       hall_ticket_sno_in_omr_user2 integer,
       hall_ticket_number_user2 VARCHAR(20),
       marks_user2 integer,
       unique(hall_ticket_number_user1,subject_code_user1,hall_ticket_number_user2,subject_code_user2)
       )""",
       """create table if not exists doublentrylabomrinfo(
       imagepath VARCHAR(400) PRIMARY KEY,
       batchcode VARCHAR(20),
       barcode_user1 VARCHAR(20),
       subject_code_user1 VARCHAR(20),
       number_of_lab_entries_user1 integer,
       grand_total_marks_user1 integer,
       barcode_user2 VARCHAR(20),
       subject_code_user2 VARCHAR(20),
       number_of_lab_entries_user2 integer,
       grand_total_marks_user2 integer
       )"""
    ]
    try:
        conn = connect_to_db(db_name)
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        conn.commit()
        cur.close()
        conn.close()
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        exit(1)
    