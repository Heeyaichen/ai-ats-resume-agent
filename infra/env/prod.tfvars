environment = "prod"
location    = "swedencentral"

# ── OpenAI model configuration ─────────────────────────────────
# Must match models available in the subscription at swedencentral.
# Validated on dev with the same model/version.
openai_chat_model_name    = "gpt-4o"
openai_chat_model_version = "2024-11-20"

# ── SKU overrides (cost-optimized production) ───────────────────
storage_replication_type = "ZRS"
openai_sku               = "S0"
openai_capacity          = 30
cosmos_throughput        = 400
redis_sku                = "Basic"
redis_capacity           = 0
search_sku               = "free"
search_replicas          = 1
apim_sku                 = "Developer_1"
static_web_app_sku       = "Free"
acr_sku                  = "Basic"
frontdoor_sku            = "Standard_AzureFrontDoor"

# Static Web Apps is not available in swedencentral.
static_web_app_location = "westeurope"

# Front Door is not supported on this subscription tier.
enable_frontdoor = false

# APIM Developer creation is blocked for free trial subscriptions.
enable_apim = false

# CORS origins: prod SWA + local dev.
cors_origins = "https://icy-hill-0eb6da303.7.azurestaticapps.net,http://localhost:5173"

apim_publisher_email = "chenkonsam@gmail.com"

# ── Shared dev resources (subscription quota limits) ───────────
# Free trial allows only 1 OpenAI account and 1 Container Apps
# Environment per region. Prod references the dev resources instead.
use_existing_openai            = true
existing_openai_name           = "ats-agent-dev-openai"
existing_openai_resource_group = "ats-agent-dev-rg"

existing_cae_id = "/subscriptions/6f6d44e3-1102-48ee-b4f9-3207cf1c63b6/resourceGroups/ats-agent-dev-rg/providers/Microsoft.App/managedEnvironments/ats-agent-dev-cae"

tags = {
  project     = "ats-agent"
  environment = "prod"
  managed_by  = "terraform"
  cost_center = "engineering"
  owner       = "chenkonsam"
}
