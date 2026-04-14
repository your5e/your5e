terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
  required_version = ">= 1.0"
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "deploy" {
  name       = "your5e-deploy"
  public_key = var.ssh_public_key
}

resource "hcloud_server" "app" {
  name        = "your5e"
  image       = "ubuntu-24.04"
  server_type = "cx23"
  location    = "nbg1"
  ssh_keys    = [hcloud_ssh_key.deploy.id]

  lifecycle {
    create_before_destroy = true
  }
}

resource "hcloud_zone" "main" {
  name = "your5e.com"
  mode = "primary"
}

resource "hcloud_zone_rrset" "root" {
  zone    = hcloud_zone.main.name
  name    = "@"
  type    = "A"
  ttl     = 300
  records = [{ value = hcloud_server.app.ipv4_address }]
}

resource "hcloud_zone_rrset" "www" {
  zone    = hcloud_zone.main.name
  name    = "www"
  type    = "A"
  ttl     = 300
  records = [{ value = hcloud_server.app.ipv4_address }]
}

resource "hcloud_zone_rrset" "api" {
  zone    = hcloud_zone.main.name
  name    = "api"
  type    = "A"
  ttl     = 300
  records = [{ value = hcloud_server.app.ipv4_address }]
}
