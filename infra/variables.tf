variable "project_name" {
  description = "Project name used in resource naming."
  type        = string
  default     = "ats-agent"
}

variable "environment" {
  description = "Deployment environment (dev or prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "swedencentral"
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default = {
    project     = "ats-agent"
    managed_by  = "terraform"
    cost_center = "engineering"
  }
}
