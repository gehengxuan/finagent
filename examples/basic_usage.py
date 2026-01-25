# examples/basic_usage.py

import os
import sys
import time
from pathlib import Path

# 确保能找到 src 目录
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

from src.agent import StructuredReportAgent
from src.utils.config import load_config, print_config


def print_environment_info():
    """打印环境信息"""
    print("\n" + "="*60)
    print("📋 环境信息")
    print("="*60)
    print(f"当前Python版本: {sys.version.split()[0]}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目根目录: {src_dir}")
    print(f"报告保存目录: {os.path.join(current_dir, '../reports')}")
    print(f"系统平台: {sys.platform}")
    print("="*60 + "\n")


def print_config_details():
    """打印详细的配置信息"""
    try:
        config = load_config()
        
        print("\n" + "="*60)
        print("⚙️  项目配置信息")
        print("="*60)
        
        # LLM 配置
        print("\n【LLM 服务配置】")
        print(f"  • 默认提供商: {config.default_llm_provider.upper()}")
        print(f"  • Qwen模型: {config.qwen_model}")
        print(f"  • DeepSeek模型: {config.deepseek_model}")
        print(f"  • OpenAI模型: {config.openai_model}")
        
        # API密钥状态
        print("\n【API密钥状态】")
        qwen_status = "✅ 已配置" if config.dashscope_api_key else "❌ 未配置"
        print(f"  • Qwen/DashScope: {qwen_status}")
        
        deepseek_status = "✅ 已配置" if config.deepseek_api_key else "❌ 未配置"
        print(f"  • DeepSeek: {deepseek_status}")
        
        openai_status = "✅ 已配置" if config.openai_api_key else "❌ 未配置"
        print(f"  • OpenAI: {openai_status}")
        
        tavily_status = "✅ 已配置" if config.tavily_api_key else "❌ 未配置"
        print(f"  • Tavily: {tavily_status}")
        
        # 搜索配置
        print("\n【搜索服务配置】")
        print(f"  • 每次查询结果数: {config.max_search_results}")
        print(f"  • 搜索超时: {config.search_timeout} 秒")
        print(f"  • 最大内容长度: {config.max_content_length} 字符")
        print(f"  • 在线搜索启用: {'✅ 是' if config.enable_online_search else '❌ 否'}")
        
        # 本地知识库
        print("\n【本地知识库配置】")
        if config.local_files:
            print(f"  • 本地文件数量: {len(config.local_files)}")
            for i, file in enumerate(config.local_files, 1):
                file_path = Path(file)
                if file_path.exists():
                    size = file_path.stat().st_size / (1024*1024)  # MB
                    print(f"    - [{i}] {file} ({size:.2f} MB)")
                else:
                    print(f"    - [{i}] {file} (⚠️  文件不存在)")
        else:
            print("  • 未配置本地文件")
        
        # Agent工作流配置
        print("\n【Agent工作流配置】")
        print(f"  • 最大反思次数: {config.max_reflections}")
        print(f"  • 最大段落数: {config.max_paragraphs}")
        
        # 输出配置
        print("\n【输出配置】")
        print(f"  • 输出目录: {config.output_dir}")
        print(f"  • 保存中间状态: {'✅ 是' if config.save_intermediate_states else '❌ 否'}")
        
        print("\n" + "="*60 + "\n")
        
        return True
    except Exception as e:
        print(f"\n⚠️  配置加载失败: {e}")
        print("请确保已正确配置 config.py 文件\n")
        return False


def main():
    """主程序"""
    
    # 1. 打印环境和配置信息
    print_environment_info()
    
    if not print_config_details():
        print("❌ 配置验证失败，程序退出")
        return
    
    # 2. 初始化 Agent
    print("🤖 正在初始化 DeepSearchAgent...")
    try:
        agent = StructuredReportAgent()
        print("✅ Agent 初始化成功\n")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        return
    
    # 3. 运行任务
    query = "分析宁德时代在新能源汽车产业链中的竞争优势及未来发展前景"
    
    print("\n" + "="*60)
    print("📝 开始生成研报")
    print("="*60)
    print(f"研报主题: {query}\n")
    
    start_time = time.time()
    
    try:
        # 这里调用封装好的 generate_report，它内部会启动 asyncio 循环
        # 整个过程包含了：生成大纲 -> 并行搜索 -> 并行写作 -> 自我反思 -> 汇总
        final_report = agent.generate_report(query)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 4. 保存结果
        output_dir = os.path.join(current_dir, "../reports/company_reports")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"report_{int(time.time())}.md"
        output_path = os.path.join(output_dir, filename)
        
        if final_report:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report)
                
            # 计算报告统计信息
            word_count = len(final_report)
            lines_count = final_report.count('\n')
            paragraphs_count = final_report.count('\n\n')
            
            print("\n" + "="*60)
            print("✅ 报告生成成功！")
            print("="*60)
            print(f"⏱️  生成耗时: {duration:.2f} 秒")
            print(f"📊 报告统计:")
            print(f"  • 字符数: {word_count:,}")
            print(f"  • 行数: {lines_count}")
            print(f"  • 段落数: {paragraphs_count}")
            print(f"📂 保存路径: {output_path}")
            print("="*60 + "\n")
        else:
            print("\n❌ 报告生成失败")
            
    except Exception as e:
        print(f"\n❌ 生成过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()