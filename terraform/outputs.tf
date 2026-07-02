output "mssql_server_internal_ip" {
  description = "The internal IP address of the MS SQL Server instance."
  value       = google_compute_instance.mssql_server.network_interface[0].network_ip
}

output "mssql_server_name" {
  description = "The GCE instance name of the MS SQL Server."
  value       = google_compute_instance.mssql_server.name
}

output "datastream_private_connection_id" {
  description = "The resource ID of the Datastream Private Connection."
  value       = google_datastream_private_connection.datastream_priv_conn.id
}
