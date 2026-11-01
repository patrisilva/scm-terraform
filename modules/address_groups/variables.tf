variable "folder" {
  description = "SCM folder for the address groups"
  type        = string
}

variable "groups" {
  description = "List of address groups to create"
  type = list(object({
    name        = string
    description = optional(string)
    members     = list(string)
  }))
  default = []
}
