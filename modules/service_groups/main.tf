terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_service_group" "this" {
  for_each = { for group in var.groups : group.name => group }

  folder  = var.folder
  name    = each.value.name
  members = each.value.members
}
