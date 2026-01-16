"""
媒体与用户提示词生成模板
基于详细的媒体画像数据生成符合媒体特征的提问
"""

from typing import Dict, Any, List, Optional

def get_media_prompt(topic: str, attributes: Dict[str, Any], context: str = "") -> str:
    """
    生成媒体提问的提示词 - 基于详细的媒体画像数据
    
    参数:
        topic: 议题
        attributes: 媒体属性（包含详细指标）
        context: 上下文信息
    
    返回:
        提示词字符串
    """
    
    # 从属性中提取各个部分
    basic_info = attributes.get("basic_info", {})
    taiwan_analysis = attributes.get("taiwan_issue_analysis", {})
    overall_performance = attributes.get("overall_performance", {})
    generation_params = attributes.get("generation_parameters", {})
    
    # 1. 媒体基本信息
    media_name = basic_info.get("name", "该媒体")
    media_country = basic_info.get("country", "未知")
    media_type = basic_info.get("media_type", "媒体")
    ownership = basic_info.get("ownership", "未知")
    political_stance = basic_info.get("political_stance", "未知")
    language = basic_info.get("language", "中文")
    
    # 2. 台湾问题分析指标（核心数据）
    total_questions = taiwan_analysis.get("total_questions", 0)
    counter_ratio = taiwan_analysis.get("counter_ratio", 0) * 100  # 转换为百分比
    aligned_ratio = taiwan_analysis.get("aligned_ratio", 0) * 100
    neutral_ratio = taiwan_analysis.get("neutral_ratio", 0) * 100
    stance_label = taiwan_analysis.get("stance_label", "未知")
    avg_question_length = taiwan_analysis.get("avg_question_length", 100)
    
    # 语义强度分数
    avg_aligned_score = taiwan_analysis.get("avg_aligned_score", 0.5)
    avg_counter_score = taiwan_analysis.get("avg_counter_score", 0.5)
    avg_neutral_score = taiwan_analysis.get("avg_neutral_score", 0.5)
    
    # 议题分布
    issue_distribution = taiwan_analysis.get("issue_distribution", {})
    taiwan_issue_ratio = taiwan_analysis.get("taiwan_issue_ratio", 0) * 100
    issue_entropy = taiwan_analysis.get("issue_entropy", 0)
    
    # 3. 总体表现
    media_total_questions = overall_performance.get("media_total_questions", 0)
    media_taihai_questions = overall_performance.get("media_taihai_questions", 0)
    taiwan_question_ratio = overall_performance.get("taiwan_question_ratio", 0) * 100
    coverage_intensity = overall_performance.get("coverage_intensity", 0) * 100
    topic_diversity = overall_performance.get("topic_diversity", 0)
    
    # 4. 生成参数
    question_style = generation_params.get("question_style", "客观中立")
    focus_priority = generation_params.get("focus_priority", {})
    challenge_level = generation_params.get("challenge_level", 0) * 100
    consistency_level = generation_params.get("consistency_level", 0) * 100
    neutral_tendency = generation_params.get("neutral_tendency", 0) * 100
    semantic_intensity = generation_params.get("semantic_intensity", 0.5)
    topic_preferences = generation_params.get("topic_preferences", {})
    
    # 构建议题关注点描述
    issue_focus_desc = build_issue_focus_description(issue_distribution, focus_priority)
    
    # 构建提问风格描述
    style_desc = build_style_description(question_style, stance_label, challenge_level)
    
    # 根据指标计算推荐的temperature
    recommended_temperature = calculate_recommended_temperature(
        neutral_ratio, consistency_level, challenge_level
    )
    
    # 构建详细的提示词
    prompt = f"""# 新闻记者提问生成指令

## 一、媒体身份与背景
你是**{media_name}**的记者，这是一家**{media_country}**的**{media_type}**（{ownership}）。

## 二、媒体特征分析（基于历史数据）

### 2.1 基本立场特征
- **总体立场标签**: {stance_label}
- **一致立场提问比例**: {aligned_ratio:.1f}%
- **对立立场提问比例**: {counter_ratio:.1f}%
- **中性立场提问比例**: {neutral_ratio:.1f}%
- **政治立场**: {political_stance}

### 2.2 提问行为特征
- **平均提问长度**: {avg_question_length:.0f}字符
- **提问总量（涉台）**: {total_questions}个问题
- **语义一致性强度**: {avg_aligned_score:.3f}
- **语义对立强度**: {avg_counter_score:.3f}
- **议题多样性指数**: {issue_entropy:.3f}

### 2.3 议题关注偏好
{taiwan_issue_ratio:.1f}%的问题聚焦台湾核心议题
{issue_focus_desc}

### 2.4 整体报道表现
- **总提问量**: {media_total_questions}个问题
- **涉台提问量**: {media_taihai_questions}个问题
- **台海议题占比**: {taiwan_question_ratio:.2f}%
- **报道强度**: {coverage_intensity:.2f}%

## 三、当前任务情境
**发布会议题**: {topic}
**背景信息**: {context if context else "常规新闻发布会"}

## 四、提问生成要求

### 4.1 立场与态度要求
1. **立场体现**: 提问必须体现 **{stance_label}** 的立场特征
   - 如为Aligned立场，应体现理解、支持或共识导向
   - 如为Counter立场，可体现质疑、挑战或对立视角
   - 如为Mixed立场，应保持平衡客观

2. **态度强度**: 
   - 一致性态度强度: {semantic_intensity:.3f}（{get_intensity_description(semantic_intensity)}）
   - 挑战性程度: {challenge_level:.1f}%
   - 中立倾向: {neutral_tendency:.1f}%

### 4.2 内容与形式要求
1. **提问风格**: {style_desc}
2. **问题长度**: 控制在{avg_question_length*0.7:.0f}-{avg_question_length*1.3:.0f}字符之间
3. **问题焦点**: 应优先关注{list(focus_priority.keys())[0] if focus_priority else "议题核心"}方面
4. **语言要求**: 使用{language}提问

### 4.3 议题相关要求
1. **议题相关性**: 问题必须直接针对"{topic}"议题
2. **专业性**: 体现{media_type}的专业性和深度
3. **新闻价值**: 问题要有新闻价值，能引发思考或讨论
4. **具体性**: 避免泛泛而谈，要有具体指向

## 五、生成示例参考
基于历史数据分析，{media_name}记者通常会：
- 提出{avg_question_length:.0f}字符左右的问题
- 采用{question_style}的提问方式
- 关注{list(topic_preferences.keys())[0] if topic_preferences else "核心议题"}

## 六、最终输出
请直接给出符合以上所有要求的提问内容，不要添加任何解释、前缀或后缀。
"""
    
    return prompt.strip()


def get_user_prompt(topic: str, attributes: Dict[str, Any], context: str = "") -> str:
    """
    生成用户评论的提示词
    
    参数:
        topic: 议题
        attributes: 用户属性
        context: 上下文信息
    
    返回:
        提示词字符串
    """
    
    # 用户基本信息
    nationality = attributes.get("nationality", "未知")
    age = attributes.get("age", "未知")
    education = attributes.get("education", "未知")
    political_leaning = attributes.get("political_leaning", "中立")
    attitude_to_china = attributes.get("attitude_to_china", "中立")
    platform = attributes.get("platform", "社交媒体")
    posting_style = attributes.get("posting_style", "一般评论")
    
    # 如果有数值型的对华态度，转换为描述
    attitude_desc = attitude_to_china
    if isinstance(attitude_to_china, (int, float)):
        if attitude_to_china > 0.6:
            attitude_desc = "非常友好/积极支持"
        elif attitude_to_china > 0.3:
            attitude_desc = "友好/支持"
        elif attitude_to_china > -0.3:
            attitude_desc = "中立/客观"
        elif attitude_to_china > -0.6:
            attitude_desc = "质疑/批评"
        else:
            attitude_desc = "强烈反对/批评"
    
    # 其他属性
    interests = attributes.get("interests", [])
    profession = attributes.get("profession", "未知")
    influence_level = attributes.get("influence_followers", 0)
    
    # 根据平台确定表达特点
    platform_style = get_platform_style(platform)
    
    # 构建提示词
    prompt = f"""# 社交媒体用户评论生成指令

## 一、用户身份信息
你是一位**{nationality}**的社交媒体用户。

## 二、用户特征
- **年龄**: {age}
- **教育背景**: {education}
- **职业**: {profession}
- **政治倾向**: {political_leaning}
- **对华态度**: {attitude_desc}
- **活跃平台**: {platform}
- **发帖风格**: {posting_style}
{f"- **兴趣领域**: {', '.join(interests) if isinstance(interests, list) else interests}" if interests else ""}
{f"- **影响力**: 约有{influence_level}名关注者" if influence_level else ""}

## 三、当前情境
**讨论议题**: {topic}
**看到的新闻/信息**: {context if context else f"关于{topic}的新闻报道"}

## 四、评论生成要求

### 4.1 身份一致性要求
1. **国籍体现**: 评论应体现{nationality}用户的视角和关切
2. **政治倾向**: 符合{political_leaning}的政治立场
3. **对华态度**: 体现{attitude_desc}的态度倾向

### 4.2 平台适应性要求
1. **平台特点**: {platform_style}
2. **表达风格**: {posting_style}
3. **内容形式**: 适合在{platform}上传播

### 4.3 内容质量要求
1. **相关性**: 直接针对"{topic}"议题
2. **观点性**: 有明确观点，不只是事实陈述
3. **个人色彩**: 体现个人背景和立场
4. **适当情绪**: 根据态度包含适当的情感色彩
5. **简洁性**: 评论长度在30-150字之间

### 4.4 语言要求
1. **语言**: 使用中文
2. **表达**: 可适当使用网络用语、表情符号或标签
3. **可读性**: 易于理解，有传播力

## 五、生成示例
典型的{platform}用户评论：
- 观点明确，立场清晰
- 语言符合平台特点
- 有个人特色
- 引发讨论或共鸣

## 六、最终输出
请直接给出符合以上要求的评论内容，不要添加任何解释。
"""
    
    return prompt.strip()


def get_media_prompt_simple(topic: str, media_name: str, country: str = "中国", 
                           stance: str = "Aligned") -> str:
    """
    简化版媒体提问提示词（用于快速测试或备用）
    
    参数:
        topic: 议题
        media_name: 媒体名称
        country: 媒体所在国家
        stance: 立场标签
    
    返回:
        提示词字符串
    """
    
    # 根据立场标签确定提问倾向
    if stance == "Aligned":
        stance_desc = "理解和支持的立场"
        tone = "建设性、合作性"
    elif stance == "Counter":
        stance_desc = "质疑和挑战的立场"
        tone = "批判性、追问性"
    else:  # Mixed或未知
        stance_desc = "平衡客观的立场"
        tone = "中立、探究性"
    
    prompt = f"""你是{country}媒体{media_name}的记者，正在参加关于"{topic}"的新闻发布会。

你的媒体通常采取{stance_desc}，提问时倾向于{tone}的语气。

请提出一个专业、有深度的问题：
1. 体现{media_name}的一贯风格
2. 问题具体明确，有针对性
3. 用中文提问
4. 长度适中，约80-150字

请直接给出问题内容："""
    
    return prompt


# ========== 辅助函数 ==========

def build_issue_focus_description(issue_distribution: Dict[str, float], 
                                  focus_priority: Dict[str, float]) -> str:
    """构建议题关注点描述"""
    
    descriptions = []
    
    # 从issue_distribution提取主要关注点
    for issue_key, ratio in issue_distribution.items():
        if ratio > 0.1:  # 只显示关注度超过10%的议题
            # 简化议题名称
            if "EI_1" in issue_key:
                desc = "外国政府涉台立法"
            elif "EI_2" in issue_key:
                desc = "外国政要涉台表态或访问"
            elif "EI_3" in issue_key:
                desc = "国际组织涉台表述"
            elif "EI_5" in issue_key:
                desc = "外媒涉台报道争议"
            elif "MS_1" in issue_key:
                desc = "外国军舰军机穿越台海"
            elif "MS_2" in issue_key:
                desc = "对台军售或军事援助"
            else:
                desc = issue_key
            
            descriptions.append(f"- {desc}: {ratio*100:.1f}%")
    
    # 从focus_priority提取优先级
    if focus_priority:
        priority_desc = "\n**关注优先级**: "
        priority_items = []
        for key, value in focus_priority.items():
            priority_items.append(f"{key}")
        priority_desc += "、".join(priority_items[:3])  # 只显示前3个
        descriptions.append(priority_desc)
    
    if not descriptions:
        return "无明显特定议题偏好"
    
    return "\n".join(descriptions)


def build_style_description(question_style: str, stance_label: str, 
                           challenge_level: float) -> str:
    """构建提问风格描述"""
    
    style_mapping = {
        "客观中立型（带有共识导向）": "客观、中立，寻求共识",
        "正式权威型": "正式、权威，体现专业性",
        "直接追问型": "直接、有力，善于追问",
        "分析探究型": "分析深入，善于探究本质",
        "平衡报道型": "平衡各方观点，全面客观"
    }
    
    base_style = style_mapping.get(question_style, question_style)
    
    # 根据挑战级别调整描述
    if challenge_level > 70:
        challenge_desc = "（高挑战性，常提出尖锐问题）"
    elif challenge_level > 30:
        challenge_desc = "（中等挑战性，适时追问）"
    else:
        challenge_desc = "（低挑战性，以建设性提问为主）"
    
    # 根据立场标签调整
    if stance_label == "Aligned":
        stance_desc = "倾向于支持性、理解性提问"
    elif stance_label == "Counter":
        stance_desc = "倾向于质疑性、批判性提问"
    else:
        stance_desc = "倾向于平衡性、中立性提问"
    
    return f"{base_style}{challenge_desc}，{stance_desc}"


def calculate_recommended_temperature(neutral_ratio: float, 
                                     consistency_level: float,
                                     challenge_level: float) -> float:
    """根据媒体特征计算推荐的大模型temperature"""
    
    # 基础温度
    base_temp = 0.7
    
    # 中性比例越高，温度可稍高（更随机）
    if neutral_ratio > 50:
        temp_adjust = 0.1
    elif neutral_ratio > 30:
        temp_adjust = 0.05
    else:
        temp_adjust = 0.0
    
    # 一致性越高，温度可稍低（更稳定）
    if consistency_level > 80:
        temp_adjust -= 0.1
    elif consistency_level > 60:
        temp_adjust -= 0.05
    
    # 挑战性越高，温度可稍高（更多变化）
    if challenge_level > 70:
        temp_adjust += 0.1
    elif challenge_level > 40:
        temp_adjust += 0.05
    
    # 确保在合理范围内
    recommended = base_temp + temp_adjust
    return max(0.3, min(0.9, recommended))


def get_intensity_description(intensity: float) -> str:
    """根据语义强度分数返回描述"""
    if intensity > 0.7:
        return "较强"
    elif intensity > 0.5:
        return "中等"
    else:
        return "较弱"


def get_platform_style(platform: str) -> str:
    """根据平台返回表达特点描述"""
    platform_styles = {
        "Twitter": "短小精悍，常使用标签(#)，观点鲜明",
        "微博": "中文表达，可包含表情符号，话题性强",
        "Facebook": "相对详细，可包含链接和图片描述",
        "YouTube": "评论常与视频内容相关，可较长",
        "Reddit": "社区化讨论，有特定板块规则",
        "知乎": "较为理性，分析性强，可较长",
        "TikTok": "简短直接，常使用流行语和表情",
        "微信": "朋友圈风格，个人化表达",
        "论坛/BBS": "讨论深入，可能有长篇回复"
    }
    
    return platform_styles.get(platform, "适应平台特点的表达方式")


# ========== 测试函数 ==========

def test_media_prompt_generation():
    """测试媒体提示词生成"""
    
    # 模拟中国日报的数据
    test_attributes = {
        "basic_info": {
            "name": "《中国日报》",
            "country": "中国",
            "media_type": "报社/纸质媒体",
            "ownership": "国有",
            "political_stance": "一致立场",
            "language": "中文"
        },
        "taiwan_issue_analysis": {
            "total_questions": 6,
            "counter_count": 0,
            "aligned_count": 4,
            "neutral_count": 2,
            "counter_ratio": 0.0,
            "aligned_ratio": 0.6666666666666666,
            "neutral_ratio": 0.3333333333333333,
            "stance_label": "Aligned",
            "avg_question_length": 83.66666666666667,
            "issue_entropy": 0.4505612088663046,
            "taiwan_issue_ratio": 0.1666666666666666,
            "avg_aligned_score": 0.62066454,
            "avg_counter_score": 0.54134893,
            "avg_neutral_score": 0.41899326,
            "issue_distribution": {
                "EI_1_外国政府涉台立法": 0.0,
                "EI_2_外国政要涉台表态或访问": 0.5,
                "EI_3_国际组织涉台表述": 0.0,
                "EI_5_外媒涉台报道争议": 0.5,
                "MS_1_外国军舰军机穿越台海": 0.0,
                "MS_2_对台军售或军事援助": 0.0
            }
        },
        "overall_performance": {
            "media_total_questions": 312,
            "media_taihai_questions": 7,
            "taiwan_question_ratio": 0.0224358974358974,
            "coverage_intensity": 0.0224,
            "topic_diversity": 0.4506
        },
        "generation_parameters": {
            "question_style": "客观中立型（带有共识导向）",
            "focus_priority": {
                "外国政要涉台表态/访问": 0.5
            },
            "challenge_level": 0.0,
            "consistency_level": 0.6666666666666666,
            "neutral_tendency": 0.3333333333333333,
            "semantic_intensity": 0.62066454,
            "topic_preferences": {
                "政要表态": 0.5
            }
        }
    }
    
    prompt = get_media_prompt(
        topic="朝韩关系紧张与地区安全",
        attributes=test_attributes,
        context="朝鲜近期发射军事侦察卫星，韩国宣布暂停《九一九军事协议》部分条款"
    )
    
    print("生成的媒体提示词示例：")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    
    # 测试推荐温度计算
    recommended_temp = calculate_recommended_temperature(
        neutral_ratio=33.3,
        consistency_level=66.7,
        challenge_level=0.0
    )
    print(f"\n推荐的大模型temperature: {recommended_temp:.2f}")


def test_user_prompt_generation():
    """测试用户提示词生成"""
    
    test_user_attributes = {
        "nationality": "美国",
        "age": "35",
        "education": "硕士",
        "political_leaning": "自由派",
        "attitude_to_china": -0.4,  # 轻度负面
        "platform": "Twitter",
        "posting_style": "理性分析",
        "interests": ["国际政治", "外交政策"],
        "profession": "研究人员"
    }
    
    prompt = get_user_prompt(
        topic="台海局势与和平稳定",
        attributes=test_user_attributes,
        context="美国军舰再次穿越台湾海峡，中方表示强烈反对"
    )
    
    print("\n生成的用户提示词示例：")
    print("=" * 80)
    print(prompt)
    print("=" * 80)


if __name__ == "__main__":
    print("提示词模板模块测试")
    print("=" * 80)
    
    test_media_prompt_generation()
    test_user_prompt_generation()
    
    print("\n测试完成！")