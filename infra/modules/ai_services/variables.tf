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

variable "openai_chat_model_name" {
  type        = string
  description = "Azure OpenAI chat model name (e.g. gpt-4o, gpt-4o-mini). Must be available in your region."
  default     = "gpt-4o"
}

variable "openai_chat_model_version" {
  type        = string
  description = "Azure OpenAI chat model version. Must be a currently supported version for your region. Check https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models"
  default     = "2025-01-01-preview"
}

variable "openai_embedding_model_name" {
  type    = string
  default = "text-embedding-ada-002"
}

variable "openai_embedding_model_version" {
  type    = string
  default = "2"
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
