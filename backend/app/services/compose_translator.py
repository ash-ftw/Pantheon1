"""Docker Compose Spec Translator — PRD Module 4 Item 2.

Parses Compose YAML files using safe_load only and extracts services, environment variables,
ports, dependencies, and volume specifications.
"""

from typing import Any

import yaml


class ComposeValidationError(Exception):
    """Raised when Compose spec is malformed or invalid."""

    pass


class ComposeTranslator:
    """Parses and translates Docker Compose files safely."""

    def parse_yaml(self, raw_yaml: str) -> dict[str, Any]:
        """Parse raw YAML string using safe_load only — PRD constraint."""
        try:
            parsed = yaml.safe_load(raw_yaml)
            if not isinstance(parsed, dict):
                raise ComposeValidationError("Invalid Compose content: Root must be a dictionary")
            return parsed
        except yaml.YAMLError as e:
            raise ComposeValidationError(f"Invalid YAML syntax: {e!s}") from e

    def extract_services(self, compose_dict: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Extract and validate services block from Compose dictionary."""
        services = compose_dict.get("services")
        if not services or not isinstance(services, dict):
            raise ComposeValidationError("Compose file must contain a 'services' mapping")

        extracted: dict[str, dict[str, Any]] = {}
        for svc_name, svc_spec in services.items():
            if not isinstance(svc_spec, dict):
                continue

            # Extract environment variables (support dict or list format)
            raw_env = svc_spec.get("environment", {})
            env_vars: dict[str, str] = {}
            if isinstance(raw_env, dict):
                env_vars = {str(k): str(v) for k, v in raw_env.items()}
            elif isinstance(raw_env, list):
                for item in raw_env:
                    if isinstance(item, str) and "=" in item:
                        k, v = item.split("=", 1)
                        env_vars[k.strip()] = v.strip()

            # Extract ports
            raw_ports = svc_spec.get("ports", [])
            ports: list[dict[str, int]] = []
            if isinstance(raw_ports, list):
                for p in raw_ports:
                    p_str = str(p)
                    if ":" in p_str:
                        parts = p_str.split(":")
                        if len(parts) == 2:
                            try:
                                ports.append(
                                    {"container_port": int(parts[1]), "host_port": int(parts[0])}
                                )
                            except ValueError:
                                pass
                    else:
                        try:
                            port_num = int(p_str)
                            ports.append({"container_port": port_num, "host_port": port_num})
                        except ValueError:
                            pass

            # Extract depends_on
            raw_deps = svc_spec.get("depends_on", [])
            depends_on: list[str] = []
            if isinstance(raw_deps, list):
                depends_on = [str(d) for d in raw_deps]
            elif isinstance(raw_deps, dict):
                depends_on = list(raw_deps.keys())

            # Extract image or build path
            image = svc_spec.get("image")
            build = svc_spec.get("build")

            extracted[svc_name] = {
                "name": svc_name,
                "image": str(image) if image else None,
                "build": build,
                "environment": env_vars,
                "ports": ports,
                "depends_on": depends_on,
            }

        return extracted


compose_translator = ComposeTranslator()
