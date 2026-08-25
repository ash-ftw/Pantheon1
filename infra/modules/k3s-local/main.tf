terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

locals {
  namespace_name = "pantheon-tenant-${var.org_id}"
}

resource "kubernetes_namespace" "tenant" {
  metadata {
    name = local.namespace_name
    labels = {
      "pantheon.io/tenant"  = var.org_id
      "pantheon.io/tier"    = var.size_tier
      "pantheon.io/managed" = "true"
    }
  }
}

resource "kubernetes_network_policy" "default_deny" {
  metadata {
    name      = "pantheon-default-deny"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]

    # Egress allowed only to Kubernetes DNS (UDP 53)
    egress {
      ports {
        protocol = "UDP"
        port     = "53"
      }
    }
  }
}

resource "kubernetes_resource_quota" "tenant_quota" {
  metadata {
    name      = "pantheon-resource-quota"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }

  spec {
    hard = {
      "pods"                   = "10"
      "requests.cpu"           = "2"
      "requests.memory"        = "4Gi"
      "limits.cpu"             = "4"
      "limits.memory"          = "8Gi"
      "requests.storage"       = "20Gi"
      "persistentvolumeclaims" = "5"
    }
  }
}

resource "kubernetes_limit_range" "tenant_limits" {
  metadata {
    name      = "pantheon-limit-range"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
    }
  }
}
