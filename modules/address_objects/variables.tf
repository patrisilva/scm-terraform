variable "folder" {
  description = "SCM folder where the address objects will be created"
  type        = string
}

variable "objects" {
  description = "List of address objects to create"
  type = list(object({
    name        = string
    kind        = optional(string, "ip_netmask")
    value       = string
    description = optional(string)
    tag         = optional(list(string), [])
  }))
  default = []
}
