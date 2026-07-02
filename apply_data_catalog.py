import os
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "your-gcp-project-id"
DATASETS = ["mssql_ods", "inventory_edw"]
TABLE_NAME = "d_oe_user"

# Portable path lookup
base_dir = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(base_dir, "pilot_data", "GCPDemo_FullPipeline_D_OE_USER.xlsx")

# Load the definition tab
df = pd.read_excel(excel_path, sheet_name=0)

# Filter out empty column names
df = df.dropna(subset=['Column Name'])
definitions = {}
for _, row in df.iterrows():
    col_name = str(row['Column Name']).strip()
    details = str(row['Details']).strip() if pd.notna(row['Details']) else ""
    sources = str(row['Data Sources']).strip() if pd.notna(row['Data Sources']) else ""
    
    desc = details
    if sources:
        desc += f" (Source: {sources})"
    definitions[col_name] = desc

print(f"Loaded {len(definitions)} column definitions.")

client = bigquery.Client(project=PROJECT_ID)

for ds in DATASETS:
    # Datastream prefixes ODS tables with schema name, e.g. "dbo_d_oe_user"
    table_id = f"{PROJECT_ID}.{ds}.dbo_{TABLE_NAME}" if ds == "mssql_ods" else f"{PROJECT_ID}.{ds}.{TABLE_NAME}"
    
    try:
        table = client.get_table(table_id)
        new_schema = []
        for field in table.schema:
            col_desc = definitions.get(field.name)
            if col_desc:
                # Update field description
                new_field = bigquery.SchemaField(
                    name=field.name,
                    field_type=field.field_type,
                    mode=field.mode,
                    description=col_desc,
                    fields=field.fields
                )
                new_schema.append(new_field)
            else:
                new_schema.append(field)
        
        table.schema = new_schema
        client.update_table(table, ["schema"])
        print(f"✅ Updated column descriptions for BigQuery table: {table_id}")
    except Exception as e:
        print(f"⚠️ Could not update schema for table {table_id}: {e}")
