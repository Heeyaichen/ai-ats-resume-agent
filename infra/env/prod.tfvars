environment = "prod"
location    = "swedencentral"

# ── OpenAI model configuration ─────────────────────────────────
# Must match models available in the subscription at swedencentral.
# Validated on dev with the same model/version.
openai_chat_model_name    = "gpt-4o"
openai_chat_model_version = "2024-11-20"

# ── SKU overrides (cost-optimized for portfolio project) ────────
storage_replication_type = "ZRS"
openai_sku               = "S0"
openai_capacity          = 30
cosmos_throughput        = 400
redis_sku                = "Basic"
redis_capacity           = 0
search_sku               = "basic"
search_replicas          = 1
apim_sku                 = "Developer_1"
static_web_app_sku       = "Free"
acr_sku                  = "Basic"
frontdoor_sku            = "Standard_AzureFrontDoor"

# Static Web Apps is not available in swedencentral.
static_web_app_location = "westeurope"

# Front Door is not supported on this subscription tier.
enable_frontdoor = false

apim_publisher_email = "chenkonsam@gmail.com"

tags = {
  project     = "ats-agent"
  environment = "prod"
  managed_by  = "terraform"
  cost_center = "engineering"
  owner       = "chenkonsam"
}
