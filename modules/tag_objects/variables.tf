variable "folder" {
  description = "SCM folder for the tag objects"
  type        = string
}

variable "tags" {
  description = "List of SCM tag objects to create"
  type = list(object({
    name  = string
    color = string
  }))
  default = []
}
