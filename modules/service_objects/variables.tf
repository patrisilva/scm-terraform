variable "folder" {
  description = "SCM folder for the service objects"
  type        = string
}

variable "services" {
  description = "List of services to create"
  type = list(object({
    name        = string
    protocol    = string
    port        = string
    description = optional(string)
  }))
  default = []
}
