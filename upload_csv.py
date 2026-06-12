# upload_csv.py
import os
import requests
from dotenv import load_data, load_dotenv

# Load variables from the .env file
load_dotenv()

CH_HOST = os.getenv("CH_HOST")
CH_USER = os.getenv("CH_USER")
CH_PASSWORD = os.getenv("CH_PASSWORD")

def upload_supplier_csv():
    print("Connecting to ClickHouse to create table and ingest supplier.csv...")
    
    url = f"https://{CH_HOST}:8443/"
    params = {
        "user": CH_USER,
        "password": CH_PASSWORD,
        "database": "default"
    }

    # 1. Drop old table structural attempts to ensure fresh mapping
    requests.post(url, params=params, data="DROP TABLE IF EXISTS default.supplier_registry")

    # 2. Create the table matching your exact CSV headers
    create_table_query = """
    CREATE TABLE default.supplier_registry (
        supplier_id String,
        name String,
        country String,
        city String,
        lat Float64,
        lon Float64,
        component String,
        lead_time_days UInt8,
        backup_supplier String,
        criticality String
    ) ENGINE = MergeTree()
    ORDER BY supplier_id
    """
    
    create_res = requests.post(url, params=params, data=create_table_query)
    if create_res.status_code != 200:
        print(f"❌ Table Creation Failed: {create_res.text}")
        return

    # 3. Open your local CSV file and stream it directly into the table
    insert_params = params.copy()
    insert_params["query"] = "INSERT INTO default.supplier_registry FORMAT CSVWithNames"
    
    try:
        with open("supplier.csv", "rb") as f:
            response = requests.post(url, params=insert_params, data=f)
            
        if response.status_code == 200:
            print("🎉 Success! Your supplier.csv rows are now inside ClickHouse Cloud.")
        else:
            print(f"❌ Ingestion Failed: {response.text}")
            
    except FileNotFoundError:
        print("❌ Error: Could not find 'supplier.csv'.")

if __name__ == "__main__":
    upload_supplier_csv()