environment = "prod"
location    = "swedencentral"

# Prod: production-grade SKUs
storage_replication_type = "ZRS"
openai_sku               = "S0"
openai_capacity          = 80
cosmos_throughput        = 1000
redis_sku                = "Premium"
redis_capacity           = 1
search_sku               = "standard"
search_replicas          = 2
apim_sku                 = "Premium_1"
static_web_app_sku       = "Standard"
acr_sku                  = "Standard"
frontdoor_sku            = "Standard_AzureFrontDoor"
apim_publisher_email     = "chenkonsam@gmail.com"

tags = {
  project     = "ats-agent"
  environment = "prod"
  managed_by  = "terraform"
  cost_center = "engineering"
  owner       = "your-team"
}
