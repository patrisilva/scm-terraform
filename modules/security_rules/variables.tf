variable "folder" {
  description = "SCM folder for the security rules"
  type        = string
}

variable "rules" {
  description = "List of security rules to create"
  type = list(object({
    name              = string
    description       = string
    action            = string
    position          = optional(string)
    relative_position = optional(string)
    target_rule       = optional(string)
    policy_type       = optional(string)
    from              = list(string)
    to                = list(string)
    source            = list(string)
    destination       = list(string)
    category          = list(string)
    application       = list(string)
    service           = list(string)
    source_user       = list(string)
    log_end           = optional(bool, false)
    disabled          = optional(bool, false)
  }))
  default = []
}
