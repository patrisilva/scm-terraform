terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_tag" "this" {
  for_each = { for tag in var.tags : tag.name => tag }

  folder = var.folder
  name   = each.value.name
  color  = each.value.color
}
