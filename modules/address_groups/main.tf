terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_address_group" "this" {
  for_each = { for group in var.groups : group.name => group }

  folder      = var.folder
  name        = each.value.name
  description = try(each.value.description, "Managed by Terraform")
  static      = each.value.members
}
