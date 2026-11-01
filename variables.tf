variable "scm_host" {
  description = "SCM API hostname. Most tenants use api.sase.paloaltonetworks.com"
  type        = string
  default     = "api.sase.paloaltonetworks.com"
}

variable "client_id" {
  description = "The service account client ID for Strata Cloud Manager"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "The service account client secret for Strata Cloud Manager"
  type        = string
  sensitive   = true
}

variable "tsg_id" {
  description = "The tenant service group ID used in the OAuth scope"
  type        = string
}

variable "folder" {
  description = "SCM folder where the objects will be created"
  type        = string
  default     = "All"
}

variable "create_administrators" {
  description = "Do not create the administrator snippet automatically. Keep this disabled unless you explicitly want Terraform to create a snippet; create it manually in SCM first and use the Python script for local-user creation."
  type        = bool
  default     = false
}
