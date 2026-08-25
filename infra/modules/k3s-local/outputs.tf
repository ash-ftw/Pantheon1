output "namespace" {
  description = "Provisioned tenant namespace name"
  value       = kubernetes_namespace.tenant.metadata[0].name
}

output "network_policy_name" {
  description = "Default deny network policy name"
  value       = kubernetes_network_policy.default_deny.metadata[0].name
}

output "resource_quota_name" {
  description = "Resource quota name"
  value       = kubernetes_resource_quota.tenant_quota.metadata[0].name
}
