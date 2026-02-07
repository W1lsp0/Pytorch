import mysql.connector
import time

config = {
    'user': 'root',
    'password': 'root123456',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'tmaa_simulation'
}

try:
    print(f"Connecting to MySQL... {config['host']}:{config['port']}")
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor(dictionary=True)
    
    # 1. Check Tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("Tables:", [t['Tables_in_tmaa_simulation'] for t in tables])
    
    # 2. Check simulation_status content
    print("\n[simulation_status] Content:")
    cursor.execute("SELECT * FROM simulation_status")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(row)
    else:
        print("Empty table.")

    # 3. Check device_profiles content (just count)
    cursor.execute("SELECT COUNT(*) as count FROM device_profiles")
    count = cursor.fetchone()['count']
    print(f"\n[device_profiles] Count: {count}")

    cursor.close()
    cnx.close()
    
except mysql.connector.Error as err:
    print(f"Error: {err}")
except Exception as e:
    print(f"General Error: {e}")
