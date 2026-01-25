"""
examples/test_modular.py
测试模块化改造后的代码
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import StructuredReportAgent
import time


def main():
    """测试入口"""
    
    print("\n" + "="*60)
    print("🧪 测试模块化改造")
    print("="*60 + "\n")
    
    try:
        # 1. 创建 Agent
        print("📌 步骤 1: 创建 Agent")
        agent = StructuredReportAgent()
        print()
        
        # 2. 生成报告
        print("📌 步骤 2: 生成报告")
        query = "分析宁德时代（300750）的投资价值，重点关注其财务表现与核心竞争力。"
        
        start_time = time.time()
        report = agent.generate_report(query)
        elapsed = time.time() - start_time
        
        print(f"\n✅ 报告生成成功! 耗时 {elapsed:.1f}s\n")
        
        # 3. 保存报告
        print("📌 步骤 3: 保存报告")
        output_dir = os.path.join(os.path.dirname(__file__), "../reports")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"report_{int(time.time())}.md"
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 报告已保存到: {output_path}")
        print(f"   大小: {len(report)} 字节\n")
        
        # 4. 显示摘要
        print("📌 步骤 4: 报告摘要")
        lines = report.split('\n')
        print("前 20 行:")
        for line in lines[:20]:
            print(f"  {line}")
        print("  ...")
        
        print("\n" + "="*60)
        print("✨ 测试完成！")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()