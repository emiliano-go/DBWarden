from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ClusterMode(Enum):
    """How DDL propagates across a ClickHouse cluster.

    NONE:        single-node / no clustering. Emit bare DDL.
    ON_CLUSTER:  append ``ON CLUSTER '<name>'`` to every DDL statement.
    REPLICATED:  target database uses ``ENGINE = Replicated``; DDL propagates
                 automatically and ``ON CLUSTER`` must be omitted.
    """
    NONE = "none"
    ON_CLUSTER = "on_cluster"
    REPLICATED = "replicated"


@dataclass(frozen=True)
class ClusterContext:
    """Resolved, immutable cluster configuration for one target database.

    Built once per migration run from the database config and passed *read-only*
    into the emit layer. Handlers never construct or mutate this; they receive it
    and ask it to decorate statements.

    Attributes:
        mode: Which propagation mode is active.
        cluster_name: The cluster name for ON_CLUSTER mode; ``None`` otherwise.
    """
    mode: ClusterMode
    cluster_name: str | None = None

    def __post_init__(self) -> None:
        if self.mode is ClusterMode.ON_CLUSTER and not self.cluster_name:
            raise ValueError("ON_CLUSTER mode requires a cluster_name")
        if self.mode is not ClusterMode.ON_CLUSTER and self.cluster_name:
            raise ValueError("cluster_name is only valid in ON_CLUSTER mode")

    @classmethod
    def from_config(cls, cfg: Any) -> "ClusterContext":
        """Resolve a ClusterContext from a database config object.

        Raises:
            ConfigurationError: if both ch_cluster and ch_replicated_database set.
        """
        cluster = getattr(cfg, "ch_cluster", None)
        replicated = getattr(cfg, "ch_replicated_database", False)
        if cluster and replicated:
            from dbwarden.exceptions import ConfigurationError
            raise ConfigurationError(
                "ch_cluster and ch_replicated_database are mutually exclusive"
            )
        if replicated:
            return cls(ClusterMode.REPLICATED)
        if cluster:
            return cls(ClusterMode.ON_CLUSTER, cluster_name=cluster)
        return cls(ClusterMode.NONE)
