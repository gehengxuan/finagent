"""Agent 初始化与配置注入测试。"""

from src.agent import StructuredReportAgent, create_agent
from src.utils.config import Config, clear_config_cache, load_config


class TestStructuredReportAgentConfigInjection:
    def setup_method(self):
        clear_config_cache()

    def teardown_method(self):
        clear_config_cache()

    def test_init_with_explicit_config(self, monkeypatch):
        sentinel_graph = object()

        monkeypatch.setattr("src.agent.GraphFactory.create_graph", lambda config=None: sentinel_graph)
        monkeypatch.setattr("src.agent.GraphFactory.get_invoke_config", lambda: {"recursion_limit": 50})

        config = Config(
            dashscope_api_key="test-key",
            default_llm_provider="qwen",
            output_dir="benchmark_runs",
            local_files=["/tmp/apple_10k.txt"],
            report_type="company",
        )

        agent = StructuredReportAgent(config=config)

        assert agent.graph is sentinel_graph
        assert agent.config.output_dir == "benchmark_runs"
        assert load_config().local_files == ["/tmp/apple_10k.txt"]

    def test_create_agent_forwards_config(self, monkeypatch):
        sentinel_graph = object()

        monkeypatch.setattr("src.agent.GraphFactory.create_graph", lambda config=None: sentinel_graph)
        monkeypatch.setattr("src.agent.GraphFactory.get_invoke_config", lambda: {"recursion_limit": 50})

        config = Config(
            dashscope_api_key="test-key",
            default_llm_provider="qwen",
        )

        agent = create_agent(config=config)
        assert agent.graph is sentinel_graph