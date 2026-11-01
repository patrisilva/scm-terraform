
locals {
  tag_rows           = csvdecode(file("${path.module}/data/tags.csv"))
  address_rows       = csvdecode(file("${path.module}/data/addresses.csv"))
  service_rows       = csvdecode(file("${path.module}/data/services.csv"))
  address_group_rows = csvdecode(file("${path.module}/data/address_groups.csv"))
  service_group_rows = csvdecode(file("${path.module}/data/service_groups.csv"))

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

