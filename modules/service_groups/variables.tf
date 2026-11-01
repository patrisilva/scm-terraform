variable "folder" {
  description = "SCM folder for the service groups"
  type        = string
}

variable "groups" {
  description = "List of service groups to create"
  type = list(object({
    name    = string
    members = list(string)
  }))
  default = []
}
