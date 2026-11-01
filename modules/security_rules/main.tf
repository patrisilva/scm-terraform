terraform {
  required_providers {
    scm = {
      source = "PaloAltoNetworks/scm"
    }
  }
}

resource "scm_security_rule" "this" {
  for_each = { for rule in var.rules : rule.name => rule }

  folder      = var.folder
  name        = each.value.name
  description = each.value.description
  action      = each.value.action

  position          = try(each.value.position, null)
  relative_position = try(each.value.relative_position, null)
  target_rule       = try(each.value.target_rule, null)
  policy_type       = try(each.value.policy_type, null)

  from        = each.value.from
  to          = each.value.to
  source      = each.value.source
  destination = each.value.destination
  category    = each.value.category
  application = each.value.application
  service     = each.value.service
  source_user = each.value.source_user
  log_end     = each.value.log_end
  disabled    = try(each.value.disabled, false)
}
