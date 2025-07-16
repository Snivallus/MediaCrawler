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

def load_data(filename):
    """加载抖音 JSON 数据文件"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_data(data):
    """处理抖音数据并返回按年份统计的结果"""
    yearly_stats = {}
    
    for item in data:
        year = datetime.fromtimestamp(item['create_time']).year
        
        if year not in yearly_stats:
            yearly_stats[year] = {
                'post_count': 0,
                'total_likes': 0,
                'total_collections': 0,
                'total_comments': 0,
                'total_shares': 0
            }
        
        yearly_stats[year]['post_count'] += 1
        yearly_stats[year]['total_likes'] += int(item.get('liked_count', 0))
        yearly_stats[year]['total_collections'] += int(item.get('collected_count', 0))
        yearly_stats[year]['total_comments'] += int(item.get('comment_count', 0))
        yearly_stats[year]['total_shares'] += int(item.get('share_count', 0))
    
    return yearly_stats

def process_weibo_jsonl(filename):
    """处理微博 JSONL 数据，按年份统计帖子数量"""
    yearly_post_count = {}

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                date_str = record.get('created_at', '')
                if not date_str:
                    continue
                # 假设格式是 "2025-07-01 12:28:00"
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                year = dt.year

                if year not in yearly_post_count:
                    yearly_post_count[year] = 0
                yearly_post_count[year] += 1
            except json.JSONDecodeError:
                continue  # 跳过格式不合法的行
    
    return yearly_post_count

def save_to_csv(stats, output_file):
    """将抖音统计结果保存为 CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Year', 'Post Count', 'Total Likes', 'Total Collections', 
                         'Total Comments', 'Total Shares'])
        
        for year in sorted(stats.keys()):
            data = stats[year]
            writer.writerow([
                year,
                data['post_count'],
                data['total_likes'],
                data['total_collections'],
                data['total_comments'],
                data['total_shares']
            ])

def save_weibo_csv(stats, output_file):
    """将微博年度发帖数保存为 CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Year', 'Post Count'])

        for year in sorted(stats.keys()):
            writer.writerow([year, stats[year]])

def plot_statistics(douyin_stats, weibo_stats, output_file):
    """绘制合并统计图表并保存为 PDF"""
    # 转为 DataFrame
    douyin_df = pd.DataFrame.from_dict(douyin_stats, orient='index')
    douyin_df = douyin_df.sort_index()

    weibo_df = pd.DataFrame.from_dict(weibo_stats, orient='index', columns=['weibo_post_count'])
    weibo_df = weibo_df.sort_index()

    # 合并年份索引
    all_years = sorted(set(douyin_df.index) | set(weibo_df.index))
    douyin_df = douyin_df.reindex(all_years, fill_value=0)
    weibo_df = weibo_df.reindex(all_years, fill_value=0)

    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    plt.figure(figsize=(14, 6))

    # 子图1：年度帖子数量
    plt.subplot(1, 2, 1)
    plt.plot(douyin_df.index, douyin_df['post_count'], marker='o', label='抖音视频数', linewidth=2)
    plt.plot(weibo_df.index, weibo_df['weibo_post_count'], marker='s', label='微博帖子数', linewidth=2)
    plt.title('年度视频/帖子数量统计', fontsize=14, pad=20)
    plt.ylabel('数量', fontsize=12)
    plt.xlabel('年份', fontsize=12)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)

    # 子图2：抖音互动数据
    plt.subplot(1, 2, 2)
    lines = douyin_df[['total_likes', 'total_collections', 'total_comments', 'total_shares']].plot(
        kind='line',
        marker='o',
        linewidth=2,
        ax=plt.gca()
    )
    plt.title('年度互动数据统计 (抖音)', fontsize=14, pad=20)
    plt.ylabel('数量', fontsize=12)
    plt.xlabel('年份', fontsize=12)
    lines.legend(['总点赞数', '总收藏数', '总评论数', '总分享数'], loc='upper left', framealpha=0.5)
    plt.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout(pad=3.0)
    plt.savefig(output_file, format='pdf', bbox_inches='tight')
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
    # douyin_input = './data/douyin/json/XuJiaHui.json'
    # weibo_input = './data/weibo/XuJiaHui.jsonl'

    # douyin_csv_output = './data/XuJiaHui_yearly_stats_douyin.csv'
    # weibo_csv_output = './data/XuJiaHui_yearly_stats_weibo.csv'
    # pdf_output = './data/XuJiaHui_yearly_stats.pdf'
    # ip_chart_output = './data/XuJiaHui_ip_location_chart.pdf'

    douyin_input = './data/douyin/json/WuKang.json'
    weibo_input = './data/weibo/WuKang.jsonl'

    douyin_csv_output = './data/WuKang_yearly_stats_douyin.csv'
    weibo_csv_output = './data/WuKang_yearly_stats_weibo.csv'
    pdf_output = './data/WuKang_yearly_stats.pdf'
    ip_chart_output = './data/WuKang_ip_location_chart.pdf'

    # 抖音数据处理
    douyin_data = load_data(douyin_input)
    douyin_stats = process_data(douyin_data)
    save_to_csv(douyin_stats, douyin_csv_output)

    # 微博数据处理
    weibo_stats = process_weibo_jsonl(weibo_input)
    save_weibo_csv(weibo_stats, weibo_csv_output)

    # 合并绘图
    plot_statistics(douyin_stats, weibo_stats, pdf_output)

    print(f"抖音统计结果已保存到 {douyin_csv_output}")
    print(f"微博统计结果已保存到 {weibo_csv_output}")
    print(f"合并图表已保存到 {pdf_output}")

    # 绘制微博 ip_location 地图
    extract_ip_locations_and_plot_map(weibo_input, ip_chart_output)

if __name__ == '__main__':
    main()
