# examples/basic_usage.py

import os
import sys
import time

# 确保能找到 src 目录
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

from src.agent import StructuredReportAgent

def main():
    # 1. 初始化 Agent
    # 这一步会构建内部的 LangGraph 图结构
    agent = StructuredReportAgent()
    
    # 2. 运行任务
    query = "分析宁德时代（300750）的投资价值，重点关注其财务表现与核心竞争力。"
    
    print("\n" + "="*50)
    print(f"开始生成研报: {query}")
    print("="*50 + "\n")
    
    start_time = time.time()
    
    # 这里调用封装好的 generate_report，它内部会启动 asyncio 循环
    # 整个过程包含了：生成大纲 -> 并行搜索 -> 并行写作 -> 自我反思 -> 汇总
    final_report = agent.generate_report(query)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 3. 保存结果
    output_dir = os.path.join(current_dir, "../reports")
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"report_{int(time.time())}.md"
    output_path = os.path.join(output_dir, filename)
    
    if final_report:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_report)
            
        print("\n" + "="*50)
        print(f"🎉 报告生成成功！耗时: {duration:.2f}秒")
        print(f"📂 保存路径: {output_path}")
        print("="*50)
    else:
        print("\n❌ 报告生成失败")

if __name__ == "__main__":
    main()