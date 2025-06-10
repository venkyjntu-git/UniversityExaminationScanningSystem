from dotenv import load_dotenv
import psycopg2
import os
from psycopg2 import OperationalError


def connect_to_db(db_name):
    # Load environment variables from the .env file
    load_dotenv()

    # Assuming environment variables are set
    conn = psycopg2.connect(
        dbname=db_name,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    return conn

# def get_databases():
#     try:
#         # Load environment variables from the .env file
#         load_dotenv()

#     # Assuming environment variables are set
#         conn = psycopg2.connect(
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT")
#         )

#         conn.autocommit = True  # Enable autocommit to execute database commands
#         cursor = conn.cursor()
        
#         # Get the list of databases
#         cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false and datname like 'results%';")
#         databases = cursor.fetchall()
        
#         # Close the connection
#         cursor.close()
#         conn.close()
        
#         return [db[0] for db in databases]  # Return a list of database names
    
#     except OperationalError as e:
#         print(f"Error: {e}")
#         return []


# def check_database_exists_or_not(db_name):
#     try:
#         # Load environment variables from the .env file
#         load_dotenv()

#     # Assuming environment variables are set
#         conn = psycopg2.connect(
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT")
#         )

#         conn.autocommit = True  # Enable autocommit to execute database commands
#         cursor = conn.cursor()
        
#         # Get the list of databases
#         cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false and datname like 'results%';")
#         databases = cursor.fetchall()
        
#         # Close the connection
#         cursor.close()
#         conn.close()
        
#         if db_name in [db[0] for db in databases]:
#             return True
#         else:
#             return False
            
#     except OperationalError as e:
#         print(f"Error: {e}")
#         return []