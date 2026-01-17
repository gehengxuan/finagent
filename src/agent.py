"""
Deep Search Agent主类
整合所有模块，实现完整的深度搜索流程
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pypdf import PdfReader

from .llms import DeepSeekLLM, OpenAILLM,BaseLLM, QwenLLM
from .nodes import (
    ReportStructureNode,
    FirstSearchNode, 
    ReflectionNode,
    FirstSummaryNode,
    ReflectionSummaryNode,
    ReportFormattingNode
)
from .state import State
from .tools import tavily_search, light_rag_search
from .utils import Config, load_config, format_search_results_for_prompt


class DeepSearchAgent:
    """Deep Search Agent主类"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化Deep Search Agent
        
        Args:
            config: 配置对象，如果不提供则自动加载
        """
        # 加载配置
        self.config = config or load_config()
        
        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()
        
        # 初始化节点
        self._initialize_nodes()
        
        # 状态
        self.state = State()
        # [新增] 自动加载配置中的本地文件
        if self.config.local_files:
            self._load_configured_files()
            
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        print(f"Deep Search Agent 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")
    
    def _initialize_llm(self) -> BaseLLM:
        """初始化LLM客户端"""
        if self.config.default_llm_provider == "qwen":
            return QwenLLM(
                api_key=self.config.qwen_api_key,
                model_name=self.config.qwen_model
            )
        elif self.config.default_llm_provider == "openai":
            return OpenAILLM(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_model
            )
        
        else:
            raise ValueError(f"不支持的LLM提供商: {self.config.default_llm_provider}")
    
    def _initialize_nodes(self):
        """初始化处理节点"""
        self.first_search_node = FirstSearchNode(self.llm_client)
        self.reflection_node = ReflectionNode(self.llm_client)
        self.first_summary_node = FirstSummaryNode(self.llm_client)
        self.reflection_summary_node = ReflectionSummaryNode(self.llm_client)
        self.report_formatting_node = ReportFormattingNode(self.llm_client)
   
    def _load_configured_files(self):
        """加载配置文件中指定的本地文件（支持 txt 和 pdf）"""
        print(f"检测到配置文件中指定了 {len(self.config.local_files)} 个目标路径...")
        loaded_docs = []
        
        # 定义支持的扩展名
        SUPPORTED_EXTENSIONS = ('.txt', '.pdf')

        def _read_single_file(file_path):
            """读取单个文件的辅助函数"""
            filename = os.path.basename(file_path)
            content = ""
            try:
                # 1. 处理 TXT 文件
                if file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                # 2. 处理 PDF 文件
                elif file_path.lower().endswith('.pdf'):
                    reader = PdfReader(file_path)
                    text_list = []
                    for page in reader.pages:
                        # 提取文本并过滤掉 None
                        page_text = page.extract_text()
                        if page_text:
                            text_list.append(page_text)
                    content = "\n".join(text_list)
                
                # 忽略其他文件
                else:
                    return None

                # 只有当提取到内容时才返回
                if content.strip():
                    return f"【来源文件: {filename}】\n{content}"
                else:
                    print(f"  [警告] 文件 {filename} 内容为空或无法提取文本")
                    return None

            except Exception as e:
                print(f"  [错误] 读取文件 {filename} 失败: {str(e)}")
                return None

        # 主循环：遍历配置路径
        for path in self.config.local_files:
            # 情况 A: 单个文件
            if os.path.isfile(path):
                if path.lower().endswith(SUPPORTED_EXTENSIONS):
                    doc = _read_single_file(path)
                    if doc:
                        loaded_docs.append(doc)
            
            # 情况 B: 文件夹
            elif os.path.isdir(path):
                print(f"  正在扫描文件夹: {path}")
                for filename in os.listdir(path):
                    full_path = os.path.join(path, filename)
                    if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                        doc = _read_single_file(full_path)
                        if doc:
                            loaded_docs.append(doc)
                            print(f"    - 已加载: {filename}")
        
        # 如果加载到了文档，存入状态
        if loaded_docs:
            self.state.manual_documents = loaded_docs
            print(f"成功自动加载了 {len(loaded_docs)} 份本地文档到 Agent 记忆中。")
        else:
            print("未加载到任何有效文档。")
    # [修改] 1. 修改 research 方法签名，增加 manual_docs 参数
    def research(self, query: str, save_report: bool = True,manual_docs: List[str] = None) -> str:
        """
        执行深度研究
        
        Args:
            query: 研究查询
            save_report: 是否保存报告到文件
            
        Returns:
            最终报告内容
        """
        print(f"\n{'='*60}")
        print(f"开始深度研究: {query}")
        print(f"{'='*60}")
        
        try:
            self.state.query = query
            # Step 1: 生成报告结构
            self._generate_report_structure(query)
            
            # Step 2: 处理每个段落
            self._process_paragraphs()
            
            # Step 3: 生成最终报告
            final_report = self._generate_final_report()
            
            # Step 4: 保存报告
            if save_report:
                self._save_report(final_report)
            
            print(f"\n{'='*60}")
            print("深度研究完成！")
            print(f"{'='*60}")
            
            return final_report
            
        except Exception as e:
            print(f"研究过程中发生错误: {str(e)}")
            raise e
    
    def _generate_report_structure(self, query: str):
        """生成报告结构"""
        print(f"\n[步骤 1] 生成报告结构...")
        
        # 创建报告结构节点
        report_structure_node = ReportStructureNode(self.llm_client, query)
        
        # 生成结构并更新状态
        self.state = report_structure_node.mutate_state(state=self.state)
        
        print(f"报告结构已生成，共 {len(self.state.paragraphs)} 个段落:")
        for i, paragraph in enumerate(self.state.paragraphs, 1):
            print(f"  {i}. {paragraph.title}")
    
    def _process_paragraphs(self):
        """处理所有段落"""
        total_paragraphs = len(self.state.paragraphs)
        
        for i in range(total_paragraphs):
            print(f"\n[步骤 2.{i+1}] 处理段落: {self.state.paragraphs[i].title}")
            print("-" * 50)
            
            # 初始搜索和总结
            self._initial_search_and_summary(i)
            
            # 反思循环
            self._reflection_loop(i)
            
            # 标记段落完成
            self.state.paragraphs[i].research.mark_completed()
            
            progress = (i + 1) / total_paragraphs * 100
            print(f"段落处理完成 ({progress:.1f}%)")
    
    def _initial_search_and_summary(self, paragraph_index: int):
        """执行初始搜索和总结"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        # 准备搜索输入
        search_input = {
            "title": paragraph.title,
            "content": paragraph.content
        }
        
        # 生成搜索查询
        print("  - 生成搜索查询...")
        search_output = self.first_search_node.run(search_input)
        search_query = search_output["search_query"]
        reasoning = search_output["reasoning"]
        
        print(f"  - 搜索查询: {search_query}")
        print(f"  - 推理: {reasoning}")
        # [修改] 这里开始修改搜索逻辑：优先使用手动文章 + 网络搜索
        search_results = []
        # 1. 处理本地文件 (始终优先)
        # ==========================================================
        if self.state.manual_documents:
            print(f"  - [本地知识库] 正在调用 {len(self.state.manual_documents)} 份本地文档...")
            for idx, doc_content in enumerate(self.state.manual_documents):
                fake_result = {
                    "title": f"本地核心资料_{idx+1}",
                    "url": "local_file",
                    "content": doc_content,
                    "score": 10.0 # 给予最高权重
                }
                search_results.append(fake_result)

        # ==========================================================
        # 2. 处理网络搜索 (由 Config 控制)
        # ==========================================================
        if self.config.enable_online_search:
            print("  - [网络搜索] 开关已开启，正在执行搜索...")
            try:
                lightrag_results = light_rag_search(
                    search_query,
                    max_results=self.config.max_search_results,
                    timeout=self.config.search_timeout,
                )
                if lightrag_results:
                    print(f"  - [网络搜索] 找到 {len(lightrag_results)} 个在线结果")
                    for j, result in enumerate(lightrag_results, 1):
                        print(f"    {j}. {result['title'][:100]}...")
                    # 将在线结果追加到本地结果后面
                    search_results.extend(lightrag_results)
                else:
                    print("  - [网络搜索] 未找到相关在线结果")
            except Exception as e:
                print(f"  - [网络搜索] 出错: {e}")
        else:
            print("  - [网络搜索] 开关已关闭，跳过联网检索。")
        # 只要 config.enable_online_search 为 True，就调用 LightRAG
        
        # 检查是否既没有本地文件，又没开网
        if not search_results:
            print("  [警告] 当前没有本地文件且关闭了网络搜索，Agent 将缺乏参考资料！")
        paragraph.research.add_search_results(search_query, search_results)
        
        # 生成初始总结
        print("  - 生成初始总结...")
        summary_input = {
            "title": paragraph.title,
            "content": paragraph.content,
            "search_query": search_query,
            "search_results": format_search_results_for_prompt(
                search_results, self.config.max_content_length
            )
        }
        
        # 更新状态
        self.state = self.first_summary_node.mutate_state(
            summary_input, self.state, paragraph_index
        )
        
        print("  - 初始总结完成")
    
    def _reflection_loop(self, paragraph_index: int):
        """执行反思循环"""
        paragraph = self.state.paragraphs[paragraph_index]
        
        for reflection_i in range(self.config.max_reflections):
            print(f"  - 反思 {reflection_i + 1}/{self.config.max_reflections}...")
            
            # 准备反思输入
            reflection_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 生成反思搜索查询
            reflection_output = self.reflection_node.run(reflection_input)
            search_query = reflection_output["search_query"]
            reasoning = reflection_output["reasoning"]
            
            print(f"    反思查询: {search_query}")
            print(f"    反思推理: {reasoning}")
            
            # 执行反思搜索
            search_results = light_rag_search(
                search_query,
                max_results=self.config.max_search_results,
                timeout=self.config.search_timeout,
                # api_key=self.config.tavily_api_key
            )
            
            if search_results:
                print(f"    找到 {len(search_results)} 个反思搜索结果")
            for j, result in enumerate(search_results, 1):
                print(f"    {j}. {result['title'][:100]}...")
            # 更新搜索历史
            paragraph.research.add_search_results(search_query, search_results)
            
            # 生成反思总结
            reflection_summary_input = {
                "title": paragraph.title,
                "content": paragraph.content,
                "search_query": search_query,
                "search_results": format_search_results_for_prompt(
                    search_results, self.config.max_content_length
                ),
                "paragraph_latest_state": paragraph.research.latest_summary
            }
            
            # 更新状态
            self.state = self.reflection_summary_node.mutate_state(
                reflection_summary_input, self.state, paragraph_index
            )
            
            print(f"    反思 {reflection_i + 1} 完成")
    
    def _generate_final_report(self) -> str:
        """生成最终报告"""
        print(f"\n[步骤 3] 生成最终报告...")
        
        # 准备报告数据
        report_data = []
        for paragraph in self.state.paragraphs:
            report_data.append({
                "title": paragraph.title,
                "paragraph_latest_state": paragraph.research.latest_summary
            })
        
        # 格式化报告
        try:
            # final_report = self.report_formatting_node.
            final_report = self.report_formatting_node.format_report_manually(
                report_data, self.state.report_title
            )
        except Exception as e:
            print(f"LLM格式化失败，使用备用方法: {str(e)}")
            final_report = self.report_formatting_node.format_report_manually(
                report_data, self.state.report_title
            )
        
        # 更新状态
        self.state.final_report = final_report
        self.state.mark_completed()
        
        print("最终报告生成完成")
        return final_report
    
    def _save_report(self, report_content: str):
        """保存报告到文件"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in self.state.query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        query_safe = query_safe.replace(' ', '_')[:30]
        
        filename = f"deep_search_report_{query_safe}_{timestamp}.md"
        filepath = os.path.join(self.config.output_dir, filename)
        
        # 保存报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"报告已保存到: {filepath}")
        
        # 保存状态（如果配置允许）
        if self.config.save_intermediate_states:
            state_filename = f"state_{query_safe}_{timestamp}.json"
            state_filepath = os.path.join(self.config.output_dir, state_filename)
            self.state.save_to_file(state_filepath)
            print(f"状态已保存到: {state_filepath}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return self.state.get_progress_summary()
    
    def load_state(self, filepath: str):
        """从文件加载状态"""
        self.state = State.load_from_file(filepath)
        print(f"状态已从 {filepath} 加载")
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        self.state.save_to_file(filepath)
        print(f"状态已保存到 {filepath}")


def create_agent(config_file: Optional[str] = None) -> DeepSearchAgent:
    """
    创建Deep Search Agent实例的便捷函数
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        DeepSearchAgent实例
    """
    config = load_config(config_file)
    return DeepSearchAgent(config)
