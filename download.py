import os
from edgar import Company, set_identity

# SEC 强制要求 API 请求必须包含 User-Agent 声明身份
# 格式必须是: "你的名字 你的邮箱"
set_identity("gehengxuan0417@gmail.com") # 运行前请换成你的真实邮箱

TARGET_TICKERS = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Amazon": "AMZN",
    "Google": "GOOGL",
    "Meta": "META",
    "JPMorgan": "JPM",
    "Tesla": "TSLA",
    "Coca-Cola": "KO"
}

def main():
    output_dir = "benchmark_10k_edgar"
    os.makedirs(output_dir, exist_ok=True)
    
    print("开始从 SEC EDGAR 官方接口拉取最新 10-K 报告...\n")

    for company_name, ticker in TARGET_TICKERS.items():
        print(f"正在获取 {company_name} ({ticker}) ...")
        try:
            # 实例化公司对象
            company = Company(ticker)
            
            # 获取该公司所有的 10-K 报告，取最新的一份 (index 0)
            # 注: 2024年部分公司的财报可能在2023年底或2025年初发布，这里直接取 available 的最新版
            filings = company.get_filings(form="10-K")
            
            if not filings:
                print(f"❌ 未找到 {company_name} 的 10-K 报告")
                continue
                
            latest_10k = filings[0]
            
            # edgartools 的杀手锏：直接提取纯文本，去除了 HTML 标签，极度适合喂给大模型或做 Chunking
            text_content = latest_10k.text()
            
            # 提取报告所属的年份/日期信息
            filing_date = latest_10k.filing_date
            
            # 保存为本地 txt 文件
            file_path = os.path.join(output_dir, f"{company_name}_10K_{filing_date}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_content)
                
            print(f"✅ 成功: {company_name} (发布日期: {filing_date}) -> 已保存")
            
        except Exception as e:
            print(f"❌ 获取 {company_name} 失败: {e}")

    print("\n🎉 全部抓取任务执行完毕！")

if __name__ == "__main__":
    main()