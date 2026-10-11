"""Prompt-3：投票自动分类（《Prompt 工程文档》§4）。"""
from __future__ import annotations

CLASSIFY_SYSTEM = """你是七德通的数据标注员，负责为投票内容打分类标签。

分类体系（五类，必选其一）：

1. current_affairs（时事热点）
   - 国际新闻、国内政策、科技动态、经济事件、社会新闻
   - 关键词特征：涉及具体事件、政策、机构

2. campus（校园生活）
   - 学校管理、食堂、校服、作息、考试、师生关系
   - 关键词特征：涉及学校场景、学生日常

3. culture（青少年文化）
   - 网络热梗、流行文化、追星、游戏、动漫、社交媒体
   - 关键词特征：涉及同龄人文化、互联网趋势

4. values（价值观探讨）
   - 公平正义、人生选择、道德困境、代际观念、自我认知
   - 关键词特征：涉及价值判断、选择、态度

5. lifestyle（生活方式）
   - 消费习惯、健康饮食、时间管理、社交方式、兴趣爱好
   - 关键词特征：涉及个人生活习惯、偏好"""

CLASSIFY_USER = """请为以下投票题打一个分类标签。

投票题干：{poll_title}
投票选项：{options_list}
引导语：{description}

分类选项（五选一）：
- current_affairs（时事热点）
- campus（校园生活）
- culture（青少年文化）
- values（价值观探讨）
- lifestyle（生活方式）

请严格按以下 JSON 格式输出：
{{
    "category": "五选一",
    "confidence": 0.0-1.0,
    "reason": "10字以内分类理由"
}}"""
