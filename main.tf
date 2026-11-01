
locals {
  tag_rows           = csvdecode(file("${path.module}/data/objects/tags.csv"))
  address_rows       = csvdecode(file("${path.module}/data/objects/addresses.csv"))
  service_rows       = csvdecode(file("${path.module}/data/services/services.csv"))
  address_group_rows = csvdecode(file("${path.module}/data/object_groups/address_groups.csv"))
  service_group_rows = csvdecode(file("${path.module}/data/service_groups/service_groups.csv"))

  rule_folder_alias = {
    "Global" = "All"
    "All"    = "All"
    "FNM"    = "FNM"
    "Lab"    = "LAB"
    "LAB"    = "LAB"
  }

  pre_rule_files  = fileset("${path.module}/data/security policies", "*_pre-rules.csv")
  post_rule_files = fileset("${path.module}/data/security policies", "*_post-rules.csv")

  pre_rule_rows = flatten([
    for file in local.pre_rule_files : [
      for row in csvdecode(file("${path.module}/data/security policies/${file}")) : merge(row, {
        folder = lookup(local.rule_folder_alias, replace(file, "_pre-rules.csv", ""), replace(file, "_pre-rules.csv", ""))
      })
      if trimspace(try(row.name, "")) != "" && !startswith(trimspace(try(row.name, "")), "#")
    ]
  ])

  post_rule_rows = flatten([
    for file in local.post_rule_files : [
      for row in csvdecode(file("${path.module}/data/security policies/${file}")) : merge(row, {
        folder = lookup(local.rule_folder_alias, replace(file, "_post-rules.csv", ""), replace(file, "_post-rules.csv", ""))
      })
      if trimspace(try(row.name, "")) != "" && !startswith(trimspace(try(row.name, "")), "#")
    ]
  ])

  pre_rules = [
    for row in local.pre_rule_rows : {
      folder          = row.folder
      name            = row.name
      description     = row.description
      action          = row.action
      position        = "pre"
      relative_position = try(row.relative_position, "") == "" ? null : row.relative_position
      target_rule     = try(row.target_rule, "") == "" ? null : row.target_rule
      policy_type     = try(row.policy_type, "") == "" ? null : row.policy_type
      from            = try(row["source zone"], row.from, "") == "" ? [] : [for value in split(",", try(row["source zone"], row.from, "")) : trimspace(value) if trimspace(value) != ""]
      to              = try(row["destination zone"], row.to, "") == "" ? [] : [for value in split(",", try(row["destination zone"], row.to, "")) : trimspace(value) if trimspace(value) != ""]
      source          = try(row["source addresses"], row.source, "") == "" ? [] : [for value in split(",", try(row["source addresses"], row.source, "")) : trimspace(value) if trimspace(value) != ""]
      destination     = try(row["destination addresses"], row.destination, "") == "" ? [] : [for value in split(",", try(row["destination addresses"], row.destination, "")) : trimspace(value) if trimspace(value) != ""]
      category        = try(row["URL Category"], row["url_category"], row.category, "") == "" ? [] : [for value in split(",", try(row["URL Category"], row["url_category"], row.category, "")) : trimspace(value) if trimspace(value) != ""]
      application     = try(row.application, "") == "" ? [] : [for value in split(",", row.application) : trimspace(value) if trimspace(value) != ""]
      service         = try(row.service, "") == "" ? [] : [for value in split(",", row.service) : trimspace(value) if trimspace(value) != ""]
      source_user     = try(row["source users"], row.source_user, "") == "" ? [] : [for value in split(",", try(row["source users"], row.source_user, "")) : trimspace(value) if trimspace(value) != ""]
      url_category    = try(row["URL Category"], row["url_category"], "") == "" ? [] : [for value in split(",", try(row["URL Category"], row["url_category"], "")) : trimspace(value) if trimspace(value) != ""]
      profile_group   = try(row["profile group"], row.profile_group, "") == "" ? null : trimspace(try(row["profile group"], row.profile_group, ""))
      log_end         = try(row.log_end, "") == "" ? false : lower(trimspace(row.log_end)) == "true"
      disabled        = try(row.disabled, "") == "" ? false : lower(trimspace(row.disabled)) == "true"
    }
  ]

  post_rules = [
    for row in local.post_rule_rows : {
      folder          = row.folder
      name            = row.name
      description     = row.description
      action          = row.action
      position        = "post"
      relative_position = try(row.relative_position, "") == "" ? null : row.relative_position
      target_rule     = try(row.target_rule, "") == "" ? null : row.target_rule
      policy_type     = try(row.policy_type, "") == "" ? null : row.policy_type
      from            = try(row["source zone"], row.from, "") == "" ? [] : [for value in split(",", try(row["source zone"], row.from, "")) : trimspace(value) if trimspace(value) != ""]
      to              = try(row["destination zone"], row.to, "") == "" ? [] : [for value in split(",", try(row["destination zone"], row.to, "")) : trimspace(value) if trimspace(value) != ""]
      source          = try(row["source addresses"], row.source, "") == "" ? [] : [for value in split(",", try(row["source addresses"], row.source, "")) : trimspace(value) if trimspace(value) != ""]
      destination     = try(row["destination addresses"], row.destination, "") == "" ? [] : [for value in split(",", try(row["destination addresses"], row.destination, "")) : trimspace(value) if trimspace(value) != ""]
      category        = try(row["URL Category"], row["url_category"], row.category, "") == "" ? [] : [for value in split(",", try(row["URL Category"], row["url_category"], row.category, "")) : trimspace(value) if trimspace(value) != ""]
      application     = try(row.application, "") == "" ? [] : [for value in split(",", row.application) : trimspace(value) if trimspace(value) != ""]
      service         = try(row.service, "") == "" ? [] : [for value in split(",", row.service) : trimspace(value) if trimspace(value) != ""]
      source_user     = try(row["source users"], row.source_user, "") == "" ? [] : [for value in split(",", try(row["source users"], row.source_user, "")) : trimspace(value) if trimspace(value) != ""]
      url_category    = try(row["URL Category"], row["url_category"], "") == "" ? [] : [for value in split(",", try(row["URL Category"], row["url_category"], "")) : trimspace(value) if trimspace(value) != ""]
      profile_group   = try(row["profile group"], row.profile_group, "") == "" ? null : trimspace(try(row["profile group"], row.profile_group, ""))
      log_end         = try(row.log_end, "") == "" ? false : lower(trimspace(row.log_end)) == "true"
      disabled        = try(row.disabled, "") == "" ? false : lower(trimspace(row.disabled)) == "true"
    }
  ]

  tag_objects = [
    for row in local.tag_rows : {
      name  = row.name
      color = row.color
    }
  ]

  address_objects = [
    for row in local.address_rows : {
      name        = row.name
      kind        = row.kind
      value       = row.value
      description = row.description
      tag         = try(row.tags, "") == "" ? [] : [for tag in split(",", row.tags) : trimspace(tag)]
    }
  ]

  address_groups = [
    for row in local.address_group_rows : {
      name        = row.name
      description = row.description
      members     = row.members == "" ? [] : [for member in split(",", row.members) : trimspace(member)]
    }
  ]

  service_objects = [
    for row in local.service_rows : {
      name        = row.name
      protocol    = row.protocol
      port        = row.port
      description = row.description
    }
  ]

  service_groups = [
    for row in local.service_group_rows : {
      name    = row.name
      members = row.members == "" ? [] : [for member in split(",", row.members) : trimspace(member)]
    }
  ]
}

module "tag_objects" {
  source = "./modules/tag_objects"

  folder = var.folder
  tags   = local.tag_objects
}

module "address_objects" {
  source = "./modules/address_objects"

  folder  = var.folder
  objects = local.address_objects

  depends_on = [module.tag_objects]
}

module "address_groups" {
  source = "./modules/address_groups"

  folder = var.folder
  groups = local.address_groups

  depends_on = [module.address_objects]
}

module "service_objects" {
  source = "./modules/service_objects"

  folder   = var.folder
  services = local.service_objects
}

module "service_groups" {
  source = "./modules/service_groups"

  folder = var.folder
  groups = local.service_groups

  depends_on = [module.service_objects]
}

module "policy_pre_rules" {
  for_each = { for folder in distinct([for rule in local.pre_rules : rule.folder]) : folder => folder }

  source = "./modules/security_rules"
  folder = each.value
  rules = [
    for rule in local.pre_rules : rule
    if rule.folder == each.value
  ]
}

module "policy_post_rules" {
  for_each = { for folder in distinct([for rule in local.post_rules : rule.folder]) : folder => folder }

  source = "./modules/security_rules"
  folder = each.value
  rules = [
    for rule in local.post_rules : rule
    if rule.folder == each.value
  ]
}

