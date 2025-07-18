import json
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from pyecharts.charts import Map
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
import re
from collections import Counter
import math
import pdfkit

def process_weibo_jsonl(filename):
    """处理微博 JSONL 数据，按年份统计帖子数量和阅读数"""
    yearly_stats = {}

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                date_str = record.get('created_at', '')
                if not date_str:
                    continue
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                year = dt.year

                if year not in yearly_stats:
                    yearly_stats[year] = {
                        'post_count': 0,
                        'reads_count': 0
                    }

                yearly_stats[year]['post_count'] += 1
                reads = record.get('reads_count', 3000) # 缺失值默认设置为3000
                # 允许 reads 是字符串或数字
                if isinstance(reads, str):
                    reads = int(reads.replace(',', '')) if reads.replace(',', '').isdigit() else 0
                elif not isinstance(reads, int):
                    reads = 0
                yearly_stats[year]['reads_count'] += reads
            except Exception:
                continue  # 跳过格式不合法的行

    return yearly_stats

def save_weibo_csv(stats, output_file):
    """将微博年度发帖数和阅读数保存为 CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Year', 'Post Count', 'Reads Count'])

        for year in sorted(stats.keys()):
            writer.writerow([year, stats[year]['post_count'], stats[year]['reads_count']])

def plot_weibo_post_and_reads(stats, output_pdf, start_year=2018):
    """绘制微博每年发帖数（左轴）与阅读数（右轴）"""
    df = pd.DataFrame.from_dict(stats, orient='index')
    df = df.sort_index()
    df = df[df.index >= start_year]

    years = df.index
    post_counts = df['post_count']
    reads_counts = df['reads_count']

    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    fig, ax1 = plt.subplots(figsize=(12, 6))

    color1 = 'tab:blue'
    ax1.set_xlabel('年份')
    ax1.set_ylabel('发帖数', color=color1)
    ax1.plot(years, post_counts, marker='o', color=color1, label='微博发帖数')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.legend(loc='upper left')

    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('阅读数', color=color2)
    ax2.plot(years, reads_counts, marker='s', linestyle='--', color=color2, label='微博阅读数')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.legend(loc='upper right')

    plt.title('微博年度发帖数与阅读数统计', fontsize=16, pad=20)
    plt.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.close()

CHINA_PROVINCES = {
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "中国香港", "中国澳门", "中国台湾"
}

CHINA_PROVINCES_MAP = {
    "北京": "北京市", 
    "天津": "天津市", 
    "上海": "上海市", 
    "重庆": "重庆市",
    "河北": "河北省", 
    "山西": "山西省", 
    "辽宁": "辽宁省", 
    "吉林": "吉林省", 
    "黑龙江": "黑龙江省",
    "江苏": "江苏省", 
    "浙江": "浙江省", 
    "安徽": "安徽省", 
    "福建": "福建省", 
    "江西": "江西省", 
    "山东": "山东省",
    "河南": "河南", 
    "湖北": "湖北省", 
    "湖南": "湖南省", 
    "广东": "广东省", 
    "海南": "海南省",
    "四川": "四川省", 
    "贵州": "贵州省", 
    "云南": "云南省", 
    "陕西": "陕西省", 
    "甘肃": "甘肃省", 
    "青海": "青海省",
    "内蒙古": "内蒙古自治区", 
    "广西": "广西壮族自治区", 
    "西藏": "西藏自治区", 
    "宁夏": "宁夏回族自治区", 
    "新疆": "新疆维吾尔自治区",
    "中国香港": "香港特别行政区", 
    "中国澳门": "澳门特别行政区", 
    "中国台湾": "台湾省"
}

def extract_ip_locations_and_plot_map(filename, output_pdf):
    """提取 IP 归属地并绘制中国地图热力图（仅保留国内 34 个省份）"""
    ip_counter = Counter()

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ip_loc = record.get('ip_location', '')

                if isinstance(ip_loc, str):
                    match = re.search(r'发布于\s*(\S+)', ip_loc)
                    if match:
                        province = match.group(1)

                        # 仅保留中国省份
                        if province in CHINA_PROVINCES:
                            ip_counter[CHINA_PROVINCES_MAP[province]] += 1
            except json.JSONDecodeError:
                continue

    if not ip_counter:
        print("无有效中国省份 IP 数据，跳过绘图.")
        return
    
    # 应用对数变换
    log_counter = {prov: math.log10(count + 1) for prov, count in ip_counter.items()}

    # 2. 转换为绘图格式
    data = [(prov, log_val) for prov, log_val in log_counter.items()]

    # 3. 绘制地图
    map_chart = (
        Map(init_opts=opts.InitOpts(width="1400px", height="900px"))  # 设置画布大小
        .add("发帖数 (log10)", data, "china")
        .set_global_opts(
            title_opts=opts.TitleOpts(title="微博发帖 IP 地图"),
            visualmap_opts=opts.VisualMapOpts(
                max_=max(log_counter.values()),
                is_piecewise=False,
                pos_left="left",
                pos_bottom="center"
            ),
            tooltip_opts=opts.TooltipOpts(
                formatter=JsCode("""
                function(params){
                    var orig = %s[params.name] || 0;
                    return params.name + ': ' + orig + ' 条';
                }
                """ % ip_counter)
            )
        )
    )

    output_html = output_pdf.replace('.pdf', '.html')
    map_chart.render(output_html)
    print(f"中国地图已保存为 HTML 文件：{output_html}")
    
    # 设置 wkhtmltopdf 的路径
    config = pdfkit.configuration(wkhtmltopdf=r'D:\Applications\wkhtmltopdf\bin\wkhtmltopdf.exe')
    pdfkit.from_file(output_html, output_pdf, configuration=config)
    print(f"中国地图已保存为 PDF 文件：{output_pdf}")

def main():
    weibo_input = './data/weibo/JinHua.jsonl'
    weibo_csv_output = './data/JinHua_yearly_stats_weibo.csv'
    pdf_output = './data/JinHua_weibo_post_reads.pdf'
    ip_chart_output = './data/JinHua_ip_location_chart.pdf'
    start_year = 2010

    # 微博数据处理
    weibo_stats = process_weibo_jsonl(weibo_input)
    save_weibo_csv(weibo_stats, weibo_csv_output)
    plot_weibo_post_and_reads(weibo_stats, pdf_output, start_year)

    print(f"微博统计结果已保存到 {weibo_csv_output}")
    print(f"微博年度图表已保存到 {pdf_output}")

    # 绘制 IP 分布图
    extract_ip_locations_and_plot_map(weibo_input, ip_chart_output)

if __name__ == '__main__':
    main()
