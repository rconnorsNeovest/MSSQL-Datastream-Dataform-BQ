#!python3
import sys
import os

# Inject user-site packages dynamically to prevent sandboxed environment import failures
user_site = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

import csv
import time
import json
import subprocess
import google.auth
from google.auth.transport.requests import Request
from google.cloud import bigquery
import requests

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
MSSQL_PASSWORD = "YourStrong!Password123"
DATASET_ODS = "mssql_ods"
DATASET_EDW = "inventory_edw"
ZONE = "us-central1-a"
REPO = "mssql-dataform-pipeline"
WORKSPACE = "mssql-transformation-workspace"

if len(sys.argv) < 2:
    print("Usage: python3 run_e2e_test_opt1.py <prefix>")
    print("Example: python3 run_e2e_test_opt1.py test01_")
    sys.exit(1)

PREFIX = sys.argv[1]
print(f"Targeting test dataset with prefix: {PREFIX}")

# 6 tables to test
TABLES = ['d_oe_user', 'NVUser3', 'UserSubService', 'AdminLogging', 'NeoDest', 'adminLoggingArchive']

CSV_FILES = {
    t: f"/path/to/workspace/test_data/{PREFIX}{t}.csv" for t in TABLES
}

# Verify files exist
for t, path in CSV_FILES.items():
    if not os.path.exists(path):
        print(f"❌ Error: CSV file does not exist: {path}")
        sys.exit(1)

def get_headers():
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    credentials.refresh(Request())
    return {
        'Authorization': f'Bearer {credentials.token}',
        'Content-Type': 'application/json'
    }

def run_mssql_query(sql_script):
    gcloud_cmd = [
        "gcloud", "compute", "ssh", "mssql-db-server",
        f"--zone={ZONE}",
        "--tunnel-through-iap",
        "--command", f"sudo docker exec -i sql1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '{MSSQL_PASSWORD}' -d InventoryDB -C"
    ]
    env = os.environ.copy()
    env["CLOUDSDK_PYTHON"] = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
    
    res = subprocess.run(gcloud_cmd, input=sql_script, text=True, capture_output=True, env=env)
    if res.returncode != 0:
        print(f"SQL command failed with error:\n{res.stderr}", flush=True)
        return False, res.stderr
    return True, res.stdout

def load_csv_data(file_path):
    rows = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def format_sql_val(col_name, val):
    if val is None or val == '' or val.upper() == 'NULL':
        return 'NULL'
        
    # Trim high-precision microseconds to milliseconds for SQL Server DATETIME compatibility
    if "-" in val and ":" in val and "." in val:
        parts = val.split(".")
        if len(parts) == 2 and len(parts[1]) > 3:
            val = parts[0] + "." + parts[1][:3]
            
    try:
        if '.' in val:
            float(val)
            return val
        else:
            int(val)
            return val
    except ValueError:
        pass
    
    escaped_val = val.replace("'", "''")
    return f"'{escaped_val}'"

def clean_existing_test_records():
    print("\n[Step 1/7] Cleaning existing test records from SQL Server and resetting IDENTITY counters...", flush=True)
    sql = """
    DELETE FROM dbo.d_oe_user;
    DELETE FROM dbo.NVUser3;
    DELETE FROM dbo.UserSubService;
    DELETE FROM dbo.AdminLogging;
    DELETE FROM dbo.NeoDest;
    DELETE FROM dbo.adminLoggingArchive;
    DBCC CHECKIDENT ('dbo.d_oe_user', RESEED, 0);
    DBCC CHECKIDENT ('dbo.UserSubService', RESEED, 0);
    DBCC CHECKIDENT ('dbo.AdminLogging', RESEED, 0);
    DBCC CHECKIDENT ('dbo.NeoDest', RESEED, 0);
    DBCC CHECKIDENT ('dbo.adminLoggingArchive', RESEED, 0);
    GO
    """
    success, out = run_mssql_query(sql)
    if success:
        print("✅ Cleanup and identity reset on SQL Server complete.", flush=True)
        
        bq_client = bigquery.Client(project=PROJECT_ID)
        
        # 1. Clean BigQuery ODS tables
        print("\n[Step 1.2/7] Cleaning BigQuery ODS staging tables...", flush=True)
        for t in TABLES:
            ods_table = f"dbo_{t}"
            query = f"DELETE FROM `{PROJECT_ID}.{DATASET_ODS}.{ods_table}` WHERE true"
            try:
                bq_client.query(query).result()
                print(f"  - Cleaned ODS table '{ods_table}'", flush=True)
            except Exception as e:
                print(f"  ⚠️ Warning: Could not clean ODS table {ods_table}: {e}", flush=True)
                
        # 2. Clean BigQuery EDW tables
        print("\n[Step 1.5/7] Cleaning BigQuery EDW dataset tables...", flush=True)
        for t in TABLES:
            query = f"DELETE FROM `{PROJECT_ID}.{DATASET_EDW}.{t}` WHERE true"
            try:
                bq_client.query(query).result()
                print(f"  - Cleaned EDW table '{t}'", flush=True)
            except Exception as e:
                print(f"  ⚠️ Warning: Could not clean EDW table {t}: {e}", flush=True)
                
        print("✅ BigQuery cleanup complete.", flush=True)
    else:
        print("❌ Cleanup failed.", flush=True)
        sys.exit(1)

def insert_test_data():
    print("\n[Step 2/7] Inserting new test records into SQL Server database...", flush=True)
    for table, path in CSV_FILES.items():
        print(f"Parsing '{table}' CSV file...", flush=True)
        rows = load_csv_data(path)
        sql_statements = []
        
        if table == "d_oe_user":
            sql_statements.append(f"SET IDENTITY_INSERT dbo.{table} ON;")
            
        for r in rows:
            cols = list(r.keys())
            vals = [format_sql_val(c, r[c]) for c in cols]
            
            insert_statement = f"INSERT INTO dbo.{table} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
            sql_statements.append(insert_statement)
            
        if table == "d_oe_user":
            sql_statements.append(f"SET IDENTITY_INSERT dbo.{table} OFF;")
        
        sql_payload = "\n".join(sql_statements) + "\nGO\n"
        print(f"Executing {len(rows)} inserts on remote SQL Server '{table}' table...", flush=True)
        success, out = run_mssql_query(sql_payload)
        if not success:
            print(f"❌ Failed to insert test data for table '{table}'!", flush=True)
            sys.exit(1)
        print(f"✅ Successfully inserted rows for table '{table}'.", flush=True)

def poll_bigquery_ods():
    print("\n[Step 3/7] Polling BigQuery ODS dataset to detect Datastream CDC replication...", flush=True)
    client = bigquery.Client(project=PROJECT_ID)
    
    max_attempts = 15
    delay = 4
    
    for i in range(max_attempts):
        print(f"Attempt {i+1}/{max_attempts}: Checking ODS tables row counts...", flush=True)
        all_synced = True
        for t in TABLES:
            ods_table = f"dbo_{t}"
            query = f"SELECT COUNT(1) as cnt FROM `{PROJECT_ID}.{DATASET_ODS}.{ods_table}`"
            try:
                job = client.query(query)
                res = list(job.result())
                cnt = res[0]['cnt'] if res else 0
                print(f"  - Table {ods_table}: {cnt} rows", flush=True)
                if cnt < 10:
                    all_synced = False
            except Exception as e:
                print(f"  Warning: Error polling ODS table {ods_table}: {e}", flush=True)
                all_synced = False
                
        if all_synced:
            print("✅ CDC sync detected! All target rows (10 per table) replicated to BigQuery ODS.", flush=True)
            return True
            
        time.sleep(delay)
        
    print("❌ Timeout: Datastream CDC replication did not sync all test data within time limit.", flush=True)
    sys.exit(1)

def trigger_dataform_transformation():
    print("\n[Step 4/7] Triggering Dataform workspace compilation & workflow execution...", flush=True)
    headers = get_headers()
    
    # 1. Compile Workspace
    print("Compiling Dataform repository workspace...", flush=True)
    compile_url = f"https://dataform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO}/compilationResults"
    compile_payload = {
        "workspace": f"projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO}/workspaces/{WORKSPACE}"
    }
    
    response = requests.post(compile_url, headers=headers, json=compile_payload)
    if response.status_code not in (200, 201):
        print(f"❌ Workspace compile request failed: {response.text}", flush=True)
        sys.exit(1)
        
    compile_res = response.json()
    compilation_result_name = compile_res.get("name")
    print(f"Workspace Compiled. Compilation ID: {compilation_result_name}", flush=True)
    
    errors = compile_res.get("codeCompilationErrors", [])
    if errors:
        print("❌ Compilation returned errors:", flush=True)
        for err in errors:
            print(err, flush=True)
        sys.exit(1)
        
    # 2. Execute Dataform Workflow
    print("Triggering Dataform pipeline execution...", flush=True)
    exec_url = f"https://dataform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO}/workflowInvocations"
    exec_payload = {
        "compilationResult": compilation_result_name,
        "invocationConfig": {
            "serviceAccount": f"123456789012-compute@developer.gserviceaccount.com"
        }
    }
    
    response = requests.post(exec_url, headers=headers, json=exec_payload)
    if response.status_code not in (200, 201):
        print(f"❌ Execute request failed: {response.text}", flush=True)
        sys.exit(1)
        
    exec_res = response.json()
    invocation_name = exec_res.get("name")
    print(f"Workflow invocation triggered. Invocation ID: {invocation_name}", flush=True)
    
    # 3. Poll execution state
    print("Polling execution state...", flush=True)
    status_url = f"https://dataform.googleapis.com/v1beta1/{invocation_name}"
    for attempt in range(60):
        time.sleep(3)
        res = requests.get(status_url, headers=headers)
        if res.status_code != 200:
            print(f"Failed to retrieve state status: {res.text}", flush=True)
            continue
        state_res = res.json()
        state = state_res.get("state")
        print(f"Dataform execution state check {attempt+1}: {state}", flush=True)
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
            
    if state == "SUCCEEDED":
        print("✅ Dataform transformation executed successfully!", flush=True)
        return True
    else:
        print(f"❌ Dataform pipeline failed with state: {state}", flush=True)
        sys.exit(1)

def fetch_bq_rows(table_name):
    client = bigquery.Client(project=PROJECT_ID)
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_EDW}.{table_name}`"
    query_job = client.query(query)
    results = query_job.result()
    return [dict(row) for row in results]

def normalize_val(val):
    if val is None or val == "" or val == "NULL" or val == "None" or str(val).upper() == "NAN":
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        try:
            if '.' in val:
                return float(val)
            else:
                return int(val)
        except ValueError:
            pass
    return str(val).strip()

def sort_rows_by_all_keys(rows):
    if not rows:
        return []
    sorted_keys = sorted(rows[0].keys())
    def get_sort_tuple(row):
        return tuple(str(normalize_val(row.get(k))) for k in sorted_keys)
    return sorted(rows, key=get_sort_tuple)

def verify_table_data(table_name, src_rows, bq_rows, mappings):
    # Add virtual 'id' mapping or use natural PK
    pk_col = mappings["pk"]
    
    # Sort both datasets to ensure matching indexes if comparing by index
    if pk_col == "virtual_id":
        src_rows_sorted = sort_rows_by_all_keys(src_rows)
        bq_rows_sorted = sort_rows_by_all_keys(bq_rows)
        
        src_dict = {i+1: src_rows_sorted[i] for i in range(len(src_rows_sorted))}
        bq_dict = {i+1: bq_rows_sorted[i] for i in range(len(bq_rows_sorted))}
    else:
        src_dict = {int(r[pk_col]): r for r in src_rows}
        bq_dict = {int(r[pk_col]): r for r in bq_rows}
        
    mismatches = 0
    matches = 0
    
    print(f"\n--- Table: {table_name} Data Validation Report ---", flush=True)
    
    for pk, src_row in src_dict.items():
        if pk not in bq_dict:
            print(f"❌ Row Key {pk}: NOT FOUND in BigQuery EDW target table!", flush=True)
            mismatches += 1
            continue
            
        bq_row = bq_dict[pk]
        row_has_mismatch = False
        
        for col in mappings["fields"]:
            expected_val = src_row.get(col)
            actual_val = bq_row.get(col)
            
            norm_exp = normalize_val(expected_val)
            norm_act = normalize_val(actual_val)
            
            # Date/Time normalization
            if col in ("LastLogin", "FirstTradeDay", "LastTradeDay", "ArchiveDate", "ApprovedDate", "AdminTimeStamp", "first_forex_provisioned_date", "zaud_created_ts", "zaud_updated_ts"):
                if norm_exp and norm_act:
                    # Compare only the first 19 chars (YYYY-MM-DD HH:MM:SS)
                    norm_exp = str(norm_exp)[:19]
                    norm_act = str(norm_act)[:19]
                    
            if norm_exp != norm_act:
                print(f"❌ Key {pk} Column Mismatch: {col} -> Source: '{norm_exp}', BigQuery: '{norm_act}'", flush=True)
                row_has_mismatch = True
                mismatches += 1
            else:
                matches += 1
                
        if not row_has_mismatch:
            print(f"✅ Row Key {pk}: Perfect match!", flush=True)
            
    print(f"Summary for {table_name}: {matches} matched fields, {mismatches} mismatches.", flush=True)
    return mismatches == 0

def run_end_to_end_comparisons():
    print("\n[Step 5/7] Fetching and comparing records from both databases side-by-side...", flush=True)
    all_passed = True
    
    # 1. d_oe_user
    oe_src = load_csv_data(CSV_FILES["d_oe_user"])
    oe_bq = fetch_bq_rows("d_oe_user")
    oe_mappings = {
        "pk": "oe_user_sk",
        "fields": ["oe_user_id", "datasource_code", "oe_user_name", "user_given_name", "smp_user_id_txt", "is_neovest_employee_ind", "is_trading_allowed_ind", "is_active_ind"]
    }
    if not verify_table_data("d_oe_user", oe_src, oe_bq, oe_mappings):
        all_passed = False
        
    # 2. NVUser3
    nv_src = load_csv_data(CSV_FILES["NVUser3"])
    nv_bq = fetch_bq_rows("NVUser3")
    nv_mappings = {
        "pk": "NV_User_ID",
        "fields": ["UserName", "Disabled", "GivenName", "Company", "EMail", "Phone", "Address", "UserType"]
    }
    if not verify_table_data("NVUser3", nv_src, nv_bq, nv_mappings):
        all_passed = False
        
    # 3. UserSubService
    uss_src = load_csv_data(CSV_FILES["UserSubService"])
    uss_bq = fetch_bq_rows("UserSubService")
    uss_mappings = {
        "pk": "virtual_id",
        "sort_key": "NV_User_ID",
        "fields": ["NV_User_ID", "Order_Value", "Service", "SubService", "EquityShares", "EquityDollars", "OptionContracts", "OptionDollars", "Billable"]
    }
    if not verify_table_data("UserSubService", uss_src, uss_bq, uss_mappings):
        all_passed = False
        
    # 4. AdminLogging
    al_src = load_csv_data(CSV_FILES["AdminLogging"])
    al_bq = fetch_bq_rows("AdminLogging")
    al_mappings = {
        "pk": "virtual_id",
        "sort_key": "AdminTimeStamp",
        "fields": ["NV_User_ID", "AdminTimeStamp", "AdminString", "AdminIdentity", "EntryType", "OrderRef", "Reason", "Server"]
    }
    if not verify_table_data("AdminLogging", al_src, al_bq, al_mappings):
        all_passed = False
        
    # 5. NeoDest
    nd_src = load_csv_data(CSV_FILES["NeoDest"])
    nd_bq = fetch_bq_rows("NeoDest")
    nd_mappings = {
        "pk": "virtual_id",
        "sort_key": "ServiceID",
        "fields": ["ServiceID", "Dest", "Broker", "ProdType", "Region", "BrokerID"]
    }
    if not verify_table_data("NeoDest", nd_src, nd_bq, nd_mappings):
        all_passed = False
        
    # 6. adminLoggingArchive
    ala_src = load_csv_data(CSV_FILES["adminLoggingArchive"])
    ala_bq = fetch_bq_rows("adminLoggingArchive")
    ala_mappings = {
        "pk": "virtual_id",
        "sort_key": "AdminTimeStamp",
        "fields": ["NV_User_ID", "AdminTimeStamp", "AdminString", "AdminIdentity", "EntryType", "OrderRef", "Reason", "Server"]
    }
    if not verify_table_data("adminLoggingArchive", ala_src, ala_bq, ala_mappings):
        all_passed = False

    print("\n" + "="*60, flush=True)
    if all_passed:
        print("✨ END-TO-END VERIFICATION PASSED: ALL DATA MATCHES PERFECTLY! ✨", flush=True)
        return True
    else:
        print("❌ END-TO-END VERIFICATION FAILED: SOME FIELD MISMATCHES WERE DETECTED.", flush=True)
        return False

def apply_metadata_catalog():
    print("\n[Step 6/7] Applying column definitions for Knowledge Catalog...", flush=True)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_script = os.path.join(base_dir, "apply_data_catalog.py")
    cmd = ["python3", catalog_script]
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode == 0:
        print("✅ Knowledge Catalog descriptions updated successfully.", flush=True)
    else:
        print(f"⚠️ Warning: Knowledge Catalog update returned code {res.returncode}:\n{res.stderr}", flush=True)

def main():
    print("============================================================", flush=True)
    print("🚀 RUNNING MODERN ELT PIPELINE END-TO-END DATA COMPARISON TEST", flush=True)
    print("============================================================", flush=True)
    # 1. Clean
    clean_existing_test_records()
    
    # 2. Insert
    insert_test_data()
    
    # 3. Poll ODS
    poll_bigquery_ods()
    
    # 4. Trigger Dataform & Wait
    trigger_dataform_transformation()
    
    # 5. Validate & Compare
    all_passed = run_end_to_end_comparisons()
    
    # 6. Apply Metadata definitions to Catalog
    apply_metadata_catalog()
    
    print("============================================================", flush=True)
    if all_passed:
        print("🟢 ALL TESTS PASSED SUCCESSFULLY!", flush=True)
        sys.exit(0)
    else:
        print("🔴 VALIDATION FAILURE: Tests failed.", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
