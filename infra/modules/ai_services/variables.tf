variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "openai_sku" {
  type    = string
  default = "S0"
}

variable "openai_capacity" {
  type    = number
  default = 30
}

variable "doc_intelligence_sku" {
  type    = string
  default = "S0"
}

variable "translator_sku" {
  type    = string
  default = "S1"
}

variable "language_sku" {
  type    = string
  default = "S"
}

variable "content_safety_sku" {
  type    = string
  default = "S0"
}
