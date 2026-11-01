terraform {
  required_version = ">= 1.5.0"

  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

provider "scm" {
  host        = var.scm_host
  client_id   = var.client_id
  client_secret = var.client_secret
  scope       = "tsg_id:${var.tsg_id}"
}
