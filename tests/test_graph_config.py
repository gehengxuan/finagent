"""
tests/test_graph_config.py
Smoke tests to verify graph_config constants are well-formed.
"""

import pytest
from src.graph.graph_config import (
    SUBGRAPH_TOPOLOGY,
    MAIN_GRAPH_TOPOLOGY,
    EXECUTION_CONFIG,
    NODE_PARAMS,
)


class TestSubgraphTopology:
    def test_has_required_keys(self):
        for key in ("name", "description", "nodes", "edges", "conditional_edges"):
            assert key in SUBGRAPH_TOPOLOGY

    def test_nodes_list(self):
        nodes = SUBGRAPH_TOPOLOGY["nodes"]
        assert isinstance(nodes, list)
        assert len(nodes) >= 4
        assert "search" in nodes
        assert "write" in nodes
        assert "reflect" in nodes
        assert "format_output" in nodes

    def test_conditional_edge_branches(self):
        cond = SUBGRAPH_TOPOLOGY["conditional_edges"][0]
        branches = cond["branches"]
        assert "end" in branches
        assert "search" in branches
        assert "rewrite" in branches


class TestMainGraphTopology:
    def test_has_required_keys(self):
        for key in ("name", "description", "nodes", "edges"):
            assert key in MAIN_GRAPH_TOPOLOGY

    def test_nodes_list(self):
        nodes = MAIN_GRAPH_TOPOLOGY["nodes"]
        assert "generate_structure" in nodes
        assert "section_worker" in nodes
        assert "compile" in nodes


class TestExecutionConfig:
    def test_has_required_keys(self):
        assert "recursion_limit" in EXECUTION_CONFIG
        assert "max_iterations_per_section" in EXECUTION_CONFIG

    def test_values_are_positive(self):
        assert EXECUTION_CONFIG["recursion_limit"] > 0
        assert EXECUTION_CONFIG["max_iterations_per_section"] > 0

    def test_max_iterations_reasonable(self):
        assert 1 <= EXECUTION_CONFIG["max_iterations_per_section"] <= 10


class TestNodeParams:
    def test_has_all_node_types(self):
        for node in ("search", "write", "reflect", "structure"):
            assert node in NODE_PARAMS

    def test_reflect_temperature_low(self):
        """Reflection should use low temperature for deterministic output."""
        assert NODE_PARAMS["reflect"]["temperature"] <= 0.5

    def test_reflect_max_tokens_sufficient(self):
        """Structured reflection needs enough tokens for JSON output."""
        assert NODE_PARAMS["reflect"]["max_tokens"] >= 1500
