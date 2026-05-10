"""
Composite CA rule policy builder.
Constructs the enabled-rule list and config from ca_rules.yaml.
"""

import yaml
import logging
from typing import Dict, Any, List, Tuple

from .epoch_scheduler import EpochScheduler

logger = logging.getLogger(__name__)


def load_ca_config(config_path: str) -> Dict[str, Any]:
    with open(config_path) as fh:
        return yaml.safe_load(fh)


def build_scheduler(
    ca_config: Dict[str, Any],
    policy_name: str,
    max_epochs: int = 20,
    neighborhood: str = "moore",
    convergence_threshold: float = 0.01,
) -> EpochScheduler:
    """
    Build an EpochScheduler from a CA config dict and policy name.
    Policy names correspond to keys under ca_config['ablations'] or
    'composite_policy' for the default full policy.
    """
    rules_cfg = ca_config.get("rules", {})

    policy_nb = neighborhood  # caller default

    if policy_name == "full_composite" or policy_name == "default":
        enabled = ca_config.get("composite_policy", {}).get("enabled_rules", [])
    else:
        ablations = ca_config.get("ablations", {})
        if policy_name not in ablations:
            logger.warning(
                "Policy '%s' not found in ca_rules.yaml; using full_composite.",
                policy_name,
            )
            enabled = ca_config.get("composite_policy", {}).get("enabled_rules", [])
        else:
            policy_spec = ablations[policy_name]
            enabled     = policy_spec.get("enabled_rules", [])
            # Per-policy neighborhood override (e.g. vonneumann_composite)
            policy_nb   = policy_spec.get("neighborhood", neighborhood)

    logger.info(
        "Building scheduler: policy=%s neighborhood=%s rules=%s",
        policy_name, policy_nb, enabled,
    )

    return EpochScheduler(
        rules_config=rules_cfg,
        enabled_rules=enabled,
        max_epochs=max_epochs,
        convergence_threshold=convergence_threshold,
        neighborhood=policy_nb,
    )


def all_policy_names(ca_config: Dict[str, Any]) -> List[str]:
    ablations = list(ca_config.get("ablations", {}).keys())
    return ["full_composite"] + [a for a in ablations if a != "full_composite"]
