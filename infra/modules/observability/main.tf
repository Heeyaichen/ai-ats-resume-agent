/**
 * Observability module — Log Analytics, Application Insights, alerts.
 * Design spec Section 10: metrics, alerts, structured logging.
 */

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.project_name}-${var.environment}-laws"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "${var.project_name}-${var.environment}-appi"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  tags                = var.tags
}

# ── Alerts (Section 10.2) ──────────────────────────────────────

resource "azurerm_monitor_metric_alert" "sb_queue_depth" {
  name                = "${var.project_name}-${var.environment}-sb-queue-depth"
  resource_group_name = var.resource_group_name
  scopes              = [var.servicebus_namespace_id]
  description         = "Service Bus queue depth above 50 for 5 minutes"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.ServiceBus/namespaces"
    metric_name      = "ActiveMessages"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 50
  }

  tags = var.tags
}

resource "azurerm_monitor_metric_alert" "container_restart" {
  name                = "${var.project_name}-${var.environment}-container-restart"
  resource_group_name = var.resource_group_name
  scopes              = [var.container_app_environment_id]
  description         = "Container App restart loop detected"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.App/managedEnvironments"
    metric_name      = "RestartCount"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 3
  }

  tags = var.tags
}
