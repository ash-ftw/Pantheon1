variable "org_id" {
  description = "Tenant Organization UUID"
  type        = string
}

variable "org_slug" {
  description = "Tenant Organization slug name"
  type        = string
}

variable "size_tier" {
  description = "Resource size tier (starter, growth, enterprise)"
  type        = string
  default     = "starter"
}
