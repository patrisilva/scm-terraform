terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_address" "this" {
  for_each = { for obj in var.objects : obj.name => obj }

  folder      = var.folder
  name        = each.value.name
  description = try(each.value.description, "Managed by Terraform")

  ip_netmask  = try(each.value.kind == "ip_netmask" ? each.value.value : null, null)
  ip_range    = try(each.value.kind == "ip_range" ? each.value.value : null, null)
  ip_wildcard = try(each.value.kind == "ip_wildcard" ? each.value.value : null, null)
  fqdn        = try(each.value.kind == "fqdn" ? each.value.value : null, null)

  tag = try(each.value.tag, [])
}
