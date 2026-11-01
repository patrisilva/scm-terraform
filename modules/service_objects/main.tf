terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_service" "this" {
  for_each = { for service in var.services : service.name => service }

  folder      = var.folder
  name        = each.value.name
  description = try(each.value.description, "Managed by Terraform")

  protocol = {
    (each.value.protocol) = {
      port = each.value.port
    }
  }
}
