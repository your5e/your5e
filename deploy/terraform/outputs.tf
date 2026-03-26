output "server_ip" {
  description = "Public IP address of the server"
  value       = hcloud_server.app.ipv4_address
}
