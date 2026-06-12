# upload_csv.py
import requests
from config import CH_HOST, CH_USER, CH_PASSWORD

def upload_supplier_csv():
    print("Connecting to ClickHouse via HTTP to initialize tables...")
    
    url = f"https://{CH_HOST}:8443/"
    params = {
        "user": CH_USER,
        "password": CH_PASSWORD,
        "database": "default"
    }

    # 1. Clear any old broken structures
    requests.post(url, params=params, data="DROP TABLE IF EXISTS default.supplier_registry")

    # 2. Create the exact schema for your CSV headers
    create_table_query = """
    CREATE TABLE default.supplier_registry (
        supplier_id String,
        company_name String,
        country String,
        city String,
        lat Float64,
        lon Float64,
        item_category String,
        lead_time_days UInt8,
        backup_supplier String,
        criticality String
    ) ENGINE = MergeTree()
    ORDER BY supplier_id
    """
    
    requests.post(url, params=params, data=create_table_query)

    # 3. Stream upload using the exact file name: 'suppliers.csv'
    insert_params = params.copy()
    insert_params["query"] = "INSERT INTO default.supplier_registry FORMAT CSVWithNames"
    
    try:
        with open("suppliers.csv", "rb") as f:
            response = requests.post(url, params=insert_params, data=f)
            
        if response.status_code == 200:
            print("🎉 Success! 'suppliers.csv' is successfully loaded into ClickHouse Cloud.")
        else:
            print(f"❌ Ingestion Failed: {response.text}")
            
    except FileNotFoundError:
        print("❌ Error: Could not find 'suppliers.csv' in this directory. Check file placement.")

if __name__ == "__main__":
    upload_supplier_csv()