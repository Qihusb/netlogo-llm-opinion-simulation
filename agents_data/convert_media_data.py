import pandas as pd
import json
import math
import os

# ===================== 手动映射字典（整合 manual_mappings.py 内容） =====================
MANUAL_COUNTRY_MAPPING = {
    "《中国日报》": "中国",
    "《人民日报》": "中国",
    "《北京青年报》": "中国",
    "《南华早报》": "中国香港",
    "《澎湃新闻》": "中国",
    "《澳大利亚人报》": "澳大利亚",
    "《环球时报》": "中国",
    "《纽约时报》": "美国",
    "中国国际电视台（CGTN）": "中国",
    "中央广播电视总台": "中国",
    "中新社": "中国",
    "俄新社": "俄罗斯",
    "俄通塔斯社": "俄罗斯",
    "印度报业托拉斯社": "印度",
    "国际广播电台": "中国",
    "彭博社": "美国",
    "总台华语环球节目中心": "中国",
    "总台央视": "中国",
    "新华社": "中国",
    "日本东京电视台": "日本",
    "日本共同社": "日本",
    "日本广播协会（NHK）": "日本",
    "法新社": "法国",
    "深圳卫视": "中国",
    "湖北广播电视台": "中国",
    "澳亚卫视": "中国澳门",
    "澳大利亚人报": "澳大利亚",
    "环球邮报": "加拿大",
    "路透社": "英国",
    "香港中评社": "中国香港",
    "香港电台": "中国香港"
}

MANUAL_OWNERSHIP_MAPPING = {
    "《中国日报》": "国有",
    "新华社": "国有",
    "中央广播电视总台": "国有",
    "《人民日报》": "国有",
    "彭博社": "私营",
    "路透社": "私营",
    "法新社": "私营",
    "《纽约时报》": "私营",
    "《北京青年报》": "国有",
    "《南华早报》": "私营",
    "《澎湃新闻》": "国有",
    "《澳大利亚人报》": "私营",
    "《环球时报》": "国有",
    "中国国际电视台（CGTN）": "国有",
    "中新社": "国有",
    "俄新社": "国有",
    "俄通塔斯社": "国有",
    "印度报业托拉斯社": "国有",
    "国际广播电台": "国有",
    "总台华语环球节目中心": "国有",
    "总台央视": "国有",
    "日本东京电视台": "私营",
    "日本共同社": "国有",
    "日本广播协会（NHK）": "国有",
    "深圳卫视": "国有",
    "湖北广播电视台": "国有",
    "澳亚卫视": "私营",
    "澳大利亚人报": "私营",
    "环球邮报": "私营",
    "香港中评社": "私营",
    "香港电台": "公营"
}

# ===================== 核心转换函数 =====================
def convert_csv_to_json(csv_filepath, output_json_path):
    """将CSV格式的媒体指标转换为JSON格式"""
    
    # 读取CSV数据（指定GBK编码，适配中文Windows文件）
    df = pd.read_csv(csv_filepath, encoding='gbk')
    
    # 自动创建输出文件夹（若输出路径包含子文件夹）
    output_dir = os.path.dirname(output_json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    media_profiles = {}
    
    for _, row in df.iterrows():
        # 生成唯一媒体ID（清理特殊字符）
        media_id = row['media_name'].lower().replace(' ', '_').replace('《', '').replace('》', '').replace('（', '').replace('）', '')
        
        # 基本类别判断（处理空值）
        stance_label = row['stance_label']
        if pd.isna(stance_label):
            stance_label = determine_stance_label(row['counter_ratio'], row['aligned_ratio'])
        
        # 构建媒体档案
        media_profiles[media_id] = {
            "basic_info": {
                "name": str(row['media_name']),
                "country": determine_country(str(row['media_name'])),
                "media_type": determine_media_type(str(row['media_name'])),
                "ownership": determine_ownership(str(row['media_name'])),
                "political_stance": map_stance_label_to_political(stance_label),
                "language": determine_language(str(row['media_name']))
            },
            
            "taiwan_issue_analysis": {
                "total_questions": int(row['total_questions']),
                "counter_count": int(row['counter_count']),
                "aligned_count": int(row['aligned_count']),
                "neutral_count": int(row['neutral_count']),
                "counter_ratio": float(row['counter_ratio']),
                "aligned_ratio": float(row['aligned_ratio']),
                "neutral_ratio": float(row['neutral_ratio']),
                "stance_label": stance_label,
                "avg_question_length": float(row['avg_question_length']),
                "issue_entropy": float(row['issue_entropy']),
                "taiwan_issue_ratio": float(row['taiwan_issue_ratio']),
                "avg_aligned_score": float(row['avg_aligned_score']),
                "avg_counter_score": float(row['avg_counter_score']),
                "avg_neutral_score": float(row['avg_neutral_score']),
                
                "issue_distribution": {
                    "EI_1_外国政府涉台立法": float(row['EI_1_外国政府涉台立法']),
                    "EI_2_外国政要涉台表态或访问": float(row['EI_2_外国政要涉台表态或访问']),
                    "EI_3_国际组织涉台表述": float(row['EI_3_国际组织涉台表述']),
                    "EI_5_外媒涉台报道争议": float(row['EI_5_外媒涉台报道争议']),
                    "MS_1_外国军舰军机穿越台海": float(row['MS_1_外国军舰军机穿越台海']),
                    "MS_2_对台军售或军事援助": float(row['MS_2_对台军售或军事援助'])
                }
            },
            
            "overall_performance": {
                "media_total_questions": int(row['media_total_questions']),
                "media_taihai_questions": int(row['media_taihai_questions']),
                "taiwan_question_ratio": float(row['taiwan_question_ratio']),
                "coverage_intensity": calculate_coverage_intensity(
                    int(row['media_taihai_questions']), 
                    int(row['media_total_questions'])
                ),
                "topic_diversity": calculate_topic_diversity(
                    float(row['issue_entropy']), 
                    stance_label  # 修复：使用已处理的stance_label，而非row['stance_label']
                )
            },
            
            "generation_parameters": {
                "question_style": determine_question_style(stance_label, row['avg_question_length']),
                "focus_priority": determine_focus_priority(row),
                "challenge_level": float(row['counter_ratio']),
                "consistency_level": float(row['aligned_ratio']),
                "neutral_tendency": float(row['neutral_ratio']),
                "semantic_intensity": float(row['avg_aligned_score']),
                "topic_preferences": extract_topic_preferences(row)
            }
        }
    
    # 保存为JSON文件（指定UTF-8编码，保留中文）
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(media_profiles, f, ensure_ascii=False, indent=2)
    
    print(f"已成功转换 {len(media_profiles)} 个媒体档案，输出文件：{output_json_path}")
    return media_profiles

# ===================== 所有辅助函数 =====================
def determine_country(media_name):
    """根据媒体名称判断国家/地区（优先使用手动映射字典）"""
    return MANUAL_COUNTRY_MAPPING.get(media_name, "未知")

def determine_stance_label(counter_ratio, aligned_ratio):
    """根据比例判断立场标签"""
    if counter_ratio > 0.6:
        return 'Counter'
    elif aligned_ratio > 0.6:
        return 'Aligned'
    else:
        return 'Mixed'

def extract_topic_preferences(row):
    """从议题分布提取主题偏好"""
    topics = {}
    if row['EI_1_外国政府涉台立法'] > 0.1:
        topics['立法议题'] = float(row['EI_1_外国政府涉台立法'])
    if row['EI_2_外国政要涉台表态或访问'] > 0.1:
        topics['政要表态'] = float(row['EI_2_外国政要涉台表态或访问'])
    if row['MS_1_外国军舰军机穿越台海'] > 0.1:
        topics['军事行动'] = float(row['MS_1_外国军舰军机穿越台海'])
    if row['MS_2_对台军售或军事援助'] > 0.1:
        topics['军售援助'] = float(row['MS_2_对台军售或军事援助'])
    
    # 如果没有明显偏好，设置默认
    if not topics:
        topics = {"外交议题": 0.5, "一般性询问": 0.5}
    
    return topics

def determine_media_type(media_name):
    """根据媒体名称判断媒体类型（如电视台、报社、通讯社等）"""
    # 定义各类媒体类型的关键词
    tv_keywords = ['央视', '卫视', 'NHK', 'CNN', 'BBC', '电视', '广播']
    news_agency_keywords = ['新华', '路透', '共同', '美联', '法新', '俄新', '塔斯', '中新社']
    newspaper_keywords = ['人民日报', '纽约', '时报', '日报', '晚报', '早报', '环球时报', '中国日报']
    online_media_keywords = ['网', '澎湃', '界面', '腾讯', '新浪']
    
    # 匹配关键词，返回对应媒体类型
    for keyword in tv_keywords:
        if keyword in media_name:
            return '电视台/广播电视媒体'
    for keyword in news_agency_keywords:
        if keyword in media_name:
            return '通讯社'
    for keyword in newspaper_keywords:
        if keyword in media_name:
            return '报社/纸质媒体'
    for keyword in online_media_keywords:
        if keyword in media_name:
            return '网络新媒体'
    
    # 无匹配时返回默认值
    return '未知媒体类型'

def determine_ownership(media_name):
    """根据媒体名称判断所有权属性（优先使用手动映射字典）"""
    return MANUAL_OWNERSHIP_MAPPING.get(media_name, "未知所有权")

def map_stance_label_to_political(stance_label):
    """将立场标签映射为具体政治立场描述"""
    stance_mapping = {
        'Counter': '对立立场',
        'Aligned': '一致立场',
        'Mixed': '中立/混合立场'
    }
    # 若标签不在映射中，返回默认值
    return stance_mapping.get(stance_label, '未知立场')

def determine_language(media_name):
    """根据媒体名称判断使用语言"""
    chinese_keywords = ['中国', '央视', '新华', '人民', '中评', '华语', '澎湃', '南华早报']
    english_keywords = ['CNN', 'BBC', '纽约', '彭博', '路透', '澳大利亚人报', '环球邮报']
    japanese_keywords = ['日本', 'NHK', '共同', '东京']
    russian_keywords = ['俄新', '塔斯']
    french_keywords = ['法新']
    
    for keyword in chinese_keywords:
        if keyword in media_name:
            return '中文'
    for keyword in english_keywords:
        if keyword in media_name:
            return '英文'
    for keyword in japanese_keywords:
        if keyword in media_name:
            return '日文'
    for keyword in russian_keywords:
        if keyword in media_name:
            return '俄文'
    for keyword in french_keywords:
        if keyword in media_name:
            return '法文'
    
    return '未知语言'

def calculate_coverage_intensity(taihai_questions, total_questions):
    """计算报道强度（台海问题提问数 / 总提问数）"""
    if total_questions == 0:
        return 0.0
    return round(taihai_questions / total_questions, 4)  # 保留4位小数，优化数据精度

def calculate_topic_diversity(issue_entropy, stance_label):
    """结合议题熵值和立场标签，计算话题多样性"""
    # 基础多样性为熵值，立场混合的媒体额外增加多样性权重
    base_diversity = float(issue_entropy)
    if stance_label == 'Mixed':
        return round(base_diversity * 1.2, 4)
    return round(base_diversity, 4)

def determine_question_style(stance_label, avg_question_length):
    """根据立场标签和平均问题长度，判断提问风格"""
    if stance_label == 'Counter':
        if avg_question_length > 50:
            return '尖锐冗长型（带有质疑导向）'
        else:
            return '简洁犀利型（带有对立导向）'
    elif stance_label == 'Aligned':
        return '客观中立型（带有共识导向）'
    else:
        if avg_question_length > 40:
            return '全面详细型（带有探究导向）'
        else:
            return '简洁中立型（带有平衡导向）'

def determine_focus_priority(row):
    """提取报道焦点优先级"""
    focus_priority = {}
    # 优先关注占比最高的议题
    topics = [
        ('EI_1_外国政府涉台立法', '外国政府涉台立法'),
        ('EI_2_外国政要涉台表态或访问', '外国政要涉台表态/访问'),
        ('MS_1_外国军舰军机穿越台海', '外国军舰军机穿越台海'),
        ('MS_2_对台军售或军事援助', '对台军售/军事援助')
    ]
    
    # 筛选占比大于0的议题，按占比排序
    topic_scores = []
    for col_name, topic_name in topics:
        score = float(row[col_name])
        if score > 0:
            topic_scores.append((topic_name, score))
    
    # 按得分排序，提取前2个焦点
    topic_scores.sort(key=lambda x: x[1], reverse=True)
    for topic_name, score in topic_scores[:2]:
        focus_priority[topic_name] = round(score, 4)
    
    # 无焦点时返回默认值
    if not focus_priority:
        focus_priority = {'一般性台海议题': 0.5}
    
    return focus_priority

# ===================== 运行入口 =====================
if __name__ == "__main__":
    # 输入CSV文件路径 + 输出JSON文件路径
    convert_csv_to_json('media_indicators.csv', 'media_profiles_enhanced.json')