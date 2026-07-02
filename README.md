# Modern ELT Data Pipeline (Option 1)

This repository implements a production-ready ELT (Extract, Load, Transform) data pipeline replicating data from **Microsoft SQL Server (CDC enabled)** to **BigQuery ODS** via **Datastream**, and transforming it into **BigQuery EDW** (Enterprise Data Warehouse) tables using **Dataform**, with automated governance metadata integration to **Knowledge Catalog**.

---

## Directory Structure
- `terraform/`: Contains all the infrastructure-as-code manifests to deploy VM, networks, firewall, IAM, BigQuery datasets, Datastream, and Dataform resources.
- `dataform/`: Local workspace repository configuration and SQLX definitions for the Dataform transformation pipeline.
- `test_data/`: Contains baseline data CSVs and split test CSVs (`test01_` through `test10_`).
- `pilot_data/`: Sample Excel source database sheets and design definitions.
- `db_bootstrap.sql`: SQL bootstrap script to initialize database, schemas, tables, and enable CDC.
- `run_e2e_test_opt1.py`: Python automation script to perform end-to-end data upload, sync verification, Dataform compilation/execution, and table matching tests.
- `apply_data_catalog.py`: Python script to parse the design document definitions and write column descriptions directly to BigQuery tables.

---

## Deployment & Run Guide

### 1. Provision Infrastructure
Run Terraform commands in the `terraform/` folder:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```
*Note: Make sure to update project/region/subnet variables in `variables.tf` as required for your destination GCP environment.*

### 2. Bootstrap MS SQL Server Database
Log in to the GCE VM via IAP SSH and execute the `db_bootstrap.sql` DDL statements to set up tables and CDC:
```bash
# Upload bootstrap file
gcloud compute scp db_bootstrap.sql mssql-db-server:/tmp/ --zone=us-central1-a --tunnel-through-iap

# Execute bootstrap script on the SQL Server docker container
gcloud compute ssh mssql-db-server --zone=us-central1-a --tunnel-through-iap --command "sudo docker exec -i sql1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'YourStrong!Password123' -i /tmp/db_bootstrap.sql -C"
```

### 3. Deploy Dataform Transformation Files
Deploy/push files from the local `dataform/` directory into your Dataform repository's development workspace via Dataform UI or the REST API.

---

## Running End-to-End Validation Tests
You can run automated E2E tests using the `run_e2e_test_opt1.py` script. The script wipes tables, loads a chunk of test records, polls BigQuery for CDC replication, compiles/triggers Dataform, and does a side-by-side verification:

```bash
# Run with any test data prefix (test01_ to test10_)
python3 run_e2e_test_opt1.py test01_
```

### Script Execution Sequence:
1. **Clean**: Deletes rows from SQL Server and BigQuery EDW/ODS.
2. **Insert**: Inserts 10 test records into SQL Server.
3. **Poll CDC**: Waits until the Datastream stream has successfully replicated the 10 rows to BigQuery ODS (`mssql_ods`).
4. **Transform**: Triggers Dataform repository compilation and execution.
5. **Compare**: Performs row-by-row comparisons of SQL Server and BigQuery EDW tables.
6. **Catalog descriptions**: Connects BQ tables to Knowledge Catalog.
