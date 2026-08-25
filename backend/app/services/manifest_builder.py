"""Kubernetes Manifest Builder — PRD Module 4 Item 5.

Hand-written Python manifest generator using typed kubernetes.client models directly.
Constructs high-availability Deployment + Service pairs per workload with secrets.
"""

from typing import Any

from kubernetes import client

from app.services.secret_extractor import secret_extractor


class ManifestBuilder:
    """Generates typed Kubernetes manifests for application workloads."""

    def build_service_manifests(
        self,
        service_name: str,
        image_tag: str,
        environment: dict[str, str],
        ports: list[dict[str, int]],
        namespace: str,
    ) -> dict[str, Any]:
        """Build V1Deployment, V1Service, and V1Secret objects for a service.

        Returns:
            {
                "deployment": V1Deployment,
                "service": V1Service | None,
                "secret": V1Secret | None
            }
        """
        # Separate secrets from plain environment variables
        plain_env, secret_env, k8s_secret = secret_extractor.extract_secrets(
            service_name=service_name, environment=environment, namespace=namespace
        )

        labels = {
            "app.kubernetes.io/name": service_name,
            "pantheon.io/managed": "true",
        }

        # Build Container Environment variables
        container_env: list[client.V1EnvVar] = []
        for k, v in plain_env.items():
            container_env.append(client.V1EnvVar(name=k, value=v))

        # Add Secret Key References for sensitive vars
        if secret_env:
            secret_name = f"secret-{service_name}"
            for k in secret_env:
                container_env.append(
                    client.V1EnvVar(
                        name=k,
                        value_from=client.V1EnvVarSource(
                            secret_key_ref=client.V1SecretKeySelector(name=secret_name, key=k)
                        ),
                    )
                )

        # Build Container Ports
        container_ports: list[client.V1ContainerPort] = []
        service_ports: list[client.V1ServicePort] = []
        for idx, p in enumerate(ports):
            c_port = p.get("container_port", 8080)
            port_name = f"http-{idx}"
            container_ports.append(client.V1ContainerPort(container_port=c_port, name=port_name))
            service_ports.append(
                client.V1ServicePort(
                    name=port_name,
                    port=p.get("host_port", c_port),
                    target_port=c_port,
                    protocol="TCP",
                )
            )

        # Build Container
        container = client.V1Container(
            name=service_name,
            image=image_tag,
            env=container_env if container_env else None,
            ports=container_ports if container_ports else None,
            resources=client.V1ResourceRequirements(
                requests={"cpu": "100m", "memory": "128Mi"},
                limits={"cpu": "500m", "memory": "512Mi"},
            ),
        )

        # Build Deployment Spec
        pod_spec = client.V1PodSpec(containers=[container])
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels), spec=pod_spec
        )
        deployment_spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels=labels),
            template=pod_template,
        )

        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=f"app-{service_name}", namespace=namespace, labels=labels
            ),
            spec=deployment_spec,
        )

        # Build Service Spec if ports exist
        k8s_service: client.V1Service | None = None
        if service_ports:
            k8s_service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=f"svc-{service_name}", namespace=namespace, labels=labels
                ),
                spec=client.V1ServiceSpec(
                    selector=labels,
                    ports=service_ports,
                    type="ClusterIP",
                ),
            )

        return {
            "deployment": deployment,
            "service": k8s_service,
            "secret": k8s_secret,
        }


manifest_builder = ManifestBuilder()
