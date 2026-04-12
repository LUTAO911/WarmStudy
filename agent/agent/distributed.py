"""
Distributed - 分布式向量库集群支持
版本: 1.0
支持: 多节点负载均衡、故障转移、数据分片
"""
import os
import time
import hashlib
import threading
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass(frozen=True)
class NodeConfig:
    host: str
    port: int
    persist_dir: str
    collection_name: str
    weight: int = 1
    max_connections: int = 100
    timeout: float = 30.0


@dataclass
class NodeStats:
    node_id: str
    status: NodeStatus
    total_requests: int = 0
    failed_requests: int = 0
    avg_latency: float = 0.0
    last_health_check: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "avg_latency": round(self.avg_latency, 3),
            "last_health_check": self.last_health_check
        }


class NodeHealthChecker:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._lock = RLock()

    def check_node(self, config: NodeConfig) -> bool:
        try:
            if not CHROMA_AVAILABLE:
                return False

            client = chromadb.PersistentClient(
                path=config.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )

            collection = client.get_or_create_collection(name=config.collection_name)
            _ = collection.count()

            return True

        except Exception as e:
            logger.warning(f"Health check failed for {config.host}:{config.port}: {e}")
            return False


class ConsistentHashRouter:
    def __init__(self, nodes: List[NodeConfig]):
        self._nodes: Dict[str, NodeConfig] = {}
        self._ring: List[Tuple[int, str]] = []
        self._virtual_nodes: int = 100
        self._lock = RLock()
        self._build_ring(nodes)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _build_ring(self, nodes: List[NodeConfig]) -> None:
        self._ring.clear()
        self._nodes.clear()

        for node in nodes:
            node_id = f"{node.host}:{node.port}"
            self._nodes[node_id] = node

            for i in range(node.weight * self._virtual_nodes):
                virtual_key = f"{node_id}#VN{i}"
                hash_key = self._hash(virtual_key)
                self._ring.append((hash_key, node_id))

        self._ring.sort(key=lambda x: x[0])

    def get_node(self, key: str) -> Optional[NodeConfig]:
        if not self._ring:
            return None

        hash_key = self._hash(key)

        left, right = 0, len(self._ring) - 1
        while left < right:
            mid = (left + right) // 2
            if self._ring[mid][0] < hash_key:
                left = mid + 1
            else:
                right = mid

        if left >= len(self._ring):
            left = 0

        node_id = self._ring[left][1]
        return self._nodes.get(node_id)

    def add_node(self, node: NodeConfig) -> None:
        with self._lock:
            node_id = f"{node.host}:{node.port}"
            self._nodes[node_id] = node

            for i in range(node.weight * self._virtual_nodes):
                virtual_key = f"{node_id}#VN{i}"
                hash_key = self._hash(virtual_key)
                self._ring.append((hash_key, node_id))

            self._ring.sort(key=lambda x: x[0])

    def remove_node(self, host: str, port: int) -> bool:
        node_id = f"{host}:{port}"

        with self._lock:
            if node_id not in self._nodes:
                return False

            del self._nodes[node_id]
            self._ring = [(h, nid) for h, nid in self._ring if nid != node_id]

        return True


class LoadBalancer:
    def __init__(self, nodes: List[NodeConfig]):
        self._nodes: Dict[str, NodeConfig] = {f"{n.host}:{n.port}": n for n in nodes}
        self._stats: Dict[str, NodeStats] = {}
        self._lock = RLock()
        self._current_index: Dict[str, int] = {}
        self._health_checker = NodeHealthChecker()

        for node in nodes:
            node_id = f"{node.host}:{node.port}"
            self._stats[node_id] = NodeStats(
                node_id=node_id,
                status=NodeStatus.HEALTHY,
                last_health_check=time.time()
            )

    def get_best_node(self, key: str = "") -> Optional[NodeConfig]:
        with self._lock:
            healthy_nodes = [
                (node_id, stats) for node_id, stats in self._stats.items()
                if stats.status == NodeStatus.HEALTHY
            ]

            if not healthy_nodes:
                return None

            min_requests = min(stats.total_requests for _, stats in healthy_nodes)

            candidates = [
                self._nodes[node_id] for node_id, stats in healthy_nodes
                if stats.total_requests == min_requests
            ]

            return candidates[0] if candidates else None

    def record_request(
        self,
        node_id: str,
        success: bool,
        latency: float
    ) -> None:
        with self._lock:
            if node_id not in self._stats:
                return

            stats = self._stats[node_id]
            stats.total_requests += 1

            if not success:
                stats.failed_requests += 1

            if stats.total_requests > 0:
                stats.avg_latency = (
                    (stats.avg_latency * (stats.total_requests - 1) + latency) /
                    stats.total_requests
                )

    def update_health(self, node_id: str, healthy: bool) -> None:
        with self._lock:
            if node_id not in self._stats:
                return

            self._stats[node_id].status = (
                NodeStatus.HEALTHY if healthy else NodeStatus.OFFLINE
            )
            self._stats[node_id].last_health_check = time.time()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                node_id: stats.to_dict()
                for node_id, stats in self._stats.items()
            }


class DistributedVectorStore:
    def __init__(
        self,
        nodes: List[NodeConfig],
        enable_failover: bool = True,
        enable_monitoring: bool = True
    ):
        self._router = ConsistentHashRouter(nodes)
        self._load_balancer = LoadBalancer(nodes)
        self._enable_failover = enable_failover
        self._enable_monitoring = enable_monitoring
        self._lock = RLock()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False

        if enable_monitoring:
            self._start_monitoring()

    def _start_monitoring(self, interval: int = 30) -> None:
        self._running = True

        def monitor_loop() -> None:
            while self._running:
                self._check_all_nodes_health()
                time.sleep(interval)

        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()

    def _check_all_nodes_health(self) -> None:
        for node_id, config in self._router._nodes.items():
            healthy = NodeHealthChecker().check_node(config)
            self._load_balancer.update_health(node_id, healthy)

    def stop_monitoring(self) -> None:
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=2)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        collection_name: str = "knowledge_base",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        node = self._router.get_node(query_text)

        if not node:
            raise RuntimeError("No available nodes")

        start_time = time.time()
        node_id = f"{node.host}:{node.port}"

        try:
            client = chromadb.PersistentClient(
                path=node.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            collection = client.get_or_create_collection(name=collection_name)

            query_params: Dict[str, Any] = {
                "query_texts": [query_text],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }

            if filters:
                query_params["where"] = filters

            results = collection.query(**query_params)

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            latency = time.time() - start_time
            self._load_balancer.record_request(node_id, True, latency)

            return list(zip(docs, metas, dists))

        except Exception as e:
            latency = time.time() - start_time
            self._load_balancer.record_request(node_id, False, latency)

            if self._enable_failover:
                return self._failover_query(query_text, n_results, collection_name, filters)

            raise

    def _failover_query(
        self,
        query_text: str,
        n_results: int,
        collection_name: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        with self._lock:
            for node_id, config in self._router._nodes.items():
                stats = self._load_balancer._stats.get(node_id)
                if stats and stats.status == NodeStatus.HEALTHY:
                    try:
                        return self._query_node(config, query_text, n_results, collection_name, filters)
                    except Exception:
                        continue

        raise RuntimeError("All nodes failed")

    def _query_node(
        self,
        node: NodeConfig,
        query_text: str,
        n_results: int,
        collection_name: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        client = chromadb.PersistentClient(
            path=node.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=collection_name)

        query_params: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }

        if filters:
            query_params["where"] = filters

        results = collection.query(**query_params)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        return list(zip(docs, metas, dists))

    def add_node(self, node: NodeConfig) -> None:
        self._router.add_node(node)
        node_id = f"{node.host}:{node.port}"
        self._load_balancer._nodes[node_id] = node
        self._load_balancer._stats[node_id] = NodeStats(
            node_id=node_id,
            status=NodeStatus.HEALTHY,
            last_health_check=time.time()
        )

    def remove_node(self, host: str, port: int) -> bool:
        node_id = f"{host}:{port}"
        success = self._router.remove_node(host, port)

        if success and node_id in self._load_balancer._nodes:
            del self._load_balancer._nodes[node_id]

        return success

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self._router._nodes),
            "healthy_nodes": sum(
                1 for stats in self._load_balancer._stats.values()
                if stats.status == NodeStatus.HEALTHY
            ),
            "node_stats": self._load_balancer.get_all_stats()
        }


class ReplicationManager:
    def __init__(
        self,
        primary_node: NodeConfig,
        replica_nodes: List[NodeConfig],
        replication_factor: int = 2
    ):
        self._primary = primary_node
        self._replicas = replica_nodes
        self._replication_factor = min(replication_factor, len(replica_nodes))
        self._lock = RLock()

    def replicate_write(
        self,
        operation: str,
        data: Dict[str, Any]
    ) -> bool:
        with self._lock:
            success_count = 0

            try:
                self._write_to_node(self._primary, operation, data)
                success_count += 1
            except Exception as e:
                logger.error(f"Primary write failed: {e}")
                return False

            for replica in self._replicas[:self._replication_factor]:
                try:
                    self._write_to_node(replica, operation, data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Replica write failed: {e}")

            return success_count >= self._replication_factor

    def _write_to_node(
        self,
        node: NodeConfig,
        operation: str,
        data: Dict[str, Any]
    ) -> None:
        if operation == "add":
            client = chromadb.PersistentClient(
                path=node.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            collection = client.get_or_create_collection(name=data["collection_name"])

            collection.add(
                embeddings=data["embeddings"],
                documents=data["documents"],
                metadatas=data["metadatas"],
                ids=data["ids"]
            )
        elif operation == "delete":
            client = chromadb.PersistentClient(
                path=node.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            collection = client.get_or_create_collection(name=data["collection_name"])
            collection.delete(ids=data["ids"])


class ShardManager:
    def __init__(self, num_shards: int = 4):
        self._num_shards = num_shards
        self._shards: Dict[int, List[NodeConfig]] = {}
        self._lock = RLock()

    def assign_shard(self, shard_id: int, nodes: List[NodeConfig]) -> None:
        with self._lock:
            self._shards[shard_id] = nodes

    def get_shard_nodes(self, key: str) -> List[NodeConfig]:
        shard_id = self._get_shard_id(key)

        with self._lock:
            return self._shards.get(shard_id, [])

    def _get_shard_id(self, key: str) -> int:
        hash_key = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_key % self._num_shards

    def get_shard_stats(self) -> Dict[int, int]:
        with self._lock:
            return {
                shard_id: len(nodes)
                for shard_id, nodes in self._shards.items()
            }


def create_distributed_store(
    config_path: str = "config/distributed_nodes.json",
) -> Optional[DistributedVectorStore]:
    import json

    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        nodes = [
            NodeConfig(
                host=n["host"],
                port=n["port"],
                persist_dir=n["persist_dir"],
                collection_name=n.get("collection_name", "knowledge_base"),
                weight=n.get("weight", 1)
            )
            for n in config.get("nodes", [])
        ]

        return DistributedVectorStore(
            nodes=nodes,
            enable_failover=config.get("enable_failover", True),
            enable_monitoring=config.get("enable_monitoring", True)
        )

    except Exception as e:
        logger.error(f"Failed to create distributed store: {e}")
        return None
