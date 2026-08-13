BRIEF_PROMPT = """你是一个课程设计报告和本科论文写作规划助手。

任务：根据项目标题和已有设定，生成一份完整的结构化 Project Brief，作为后续生成大纲和章节正文的唯一事实来源。

写作类型：{project_type}
项目标题：{project_title}
专业：{major}
学校：{school}
目标字数：{target_word_count}
任务要求：{requirements}

要求：
1. 必须根据标题推断并写全 background、core_problem、goal、significance、technical_route、modules、expected_result、writing_boundary、title_explanation、locked_facts。
2. 各正文字段都要写成可用的完整段落或列表，不要留空字符串。
3. 内容应像一份可执行的课程设计/论文写作依据，紧扣标题，不要写成“信息不足”的占位句。
4. missing_info 只放学校格式、具体实验数据等无法从标题合理推断的项；不要把背景、问题、目标放进 missing_info。
5. 输出 JSON，不要输出 Markdown。

输出结构：
{{
  "title_explanation": "",
  "background": "",
  "core_problem": "",
  "goal": "",
  "significance": "",
  "technical_route": "",
  "modules": [],
  "expected_result": "",
  "writing_boundary": "",
  "missing_info": [],
  "locked_facts": []
}}
"""

OUTLINE_PROMPT = """你是一个本科论文和课程设计报告大纲设计助手。

任务：根据 Project Brief 为用户生成结构合理、前后递进的大纲。

写作类型：{project_type}
目标字数：{target_word_count}
学校或教师要求：{requirements}
Project Brief：{project_brief}
大纲偏好：{outline_preference}

要求：为每个章节给出 purpose 和 suggested_word_count；输出 JSON，不要输出 Markdown。

输出结构：
{{
  "chapters": [
    {{
      "title": "",
      "level": 1,
      "order": 1,
      "purpose": "",
      "suggested_word_count": 1200,
      "children": []
    }}
  ]
}}
"""

RELATION_PROMPT = """你是一个论文结构规划助手，擅长建立章节之间的承接关系。

任务：根据 Project Brief 和已确认大纲，为每个一级章节生成章节关系说明。

Project Brief：{project_brief}
完整大纲：{outline}

要求：说明前后承接、依赖事实、关键点、输出结论和避免重复内容；输出 JSON，不要输出 Markdown。

输出结构：
{{
  "relations": [
    {{
      "chapter_title": "",
      "purpose": "",
      "previous_bridge": "",
      "next_bridge": "",
      "required_questions": [],
      "depends_on_facts": [],
      "key_points": [],
      "output_conclusions": [],
      "avoid_repeating": []
    }}
  ]
}}
"""

CHAPTER_DRAFT_PROMPT = """你是一个本科论文和课程设计报告初稿写作助手。

任务：根据当前章节目标和上下文，生成当前章节正文初稿。

写作类型：{project_type}
项目标题：{project_title}
Project Brief：{project_brief}
完整大纲：{outline}
已完成章节摘要：{previous_summaries}
当前章节：{current_chapter}
当前章节关系：{current_relation}
相关用户材料：{related_materials}
用户额外要求：{user_instruction}

要求：只写当前章节；不得编造用户未提供的信息；缺失信息使用“[待补充：具体信息]”；输出 Markdown。
表格用 Markdown 表格，上一行写中文题注且不要自编号，例如“表 用户基本信息”。独立公式用 $$...$$，行内公式用 $...$，不要自编号。
"""

CHAPTER_SUMMARY_PROMPT = """你是一个论文上下文压缩助手。

任务：阅读当前章节正文，生成供后续章节使用的结构化摘要。

章节标题：{chapter_title}
章节正文：{chapter_content}

要求：提取关键结论、已使用事实和对后续章节的影响；输出 JSON，不要输出 Markdown。

输出结构：
{{
  "summary": "",
  "key_conclusions": [],
  "used_facts": [],
  "forward_implications": []
}}
"""

PAPER_ABSTRACT_PROMPT = """你是一个本科论文和课程设计报告摘要写作助手。

任务：根据论文标题、Project Brief 和已完成章节正文，生成中英文摘要、英文标题和关键词。摘要是文前独立内容，不是正文章节。

写作类型：{project_type}
中文标题：{project_title}
Project Brief：{project_brief}
章节正文：{chapter_drafts}

要求：
1. abstract_zh 用中文概括研究背景、方法、主要工作和结论，约 300–500 字，不要写成章节目录。
2. abstract_en 与中文摘要内容对应，使用规范学术英语。
3. title_en 是中文标题的准确英译，专有名词保持通行译法。
4. keywords_zh 给出 3–6 个中文关键词；keywords_en 与之对应。
5. 不得编造章节正文中没有的实验结果或数据。
6. 输出 JSON，不要输出 Markdown。

输出结构：
{{
  "title_en": "",
  "abstract_zh": "",
  "abstract_en": "",
  "keywords_zh": [],
  "keywords_en": []
}}
"""

CONSISTENCY_REVIEW_PROMPT = """你是一个论文和课程设计报告审稿助手。

任务：检查全文初稿在结构、事实、术语和章节衔接上的一致性。

Project Brief：{project_brief}
完整大纲：{outline}
章节关系：{relations}
章节正文：{chapter_drafts}

要求：输出问题列表和修改建议；输出 JSON，不要输出 Markdown。

输出结构：
{{
  "issues": [
    {{
      "severity": "low | medium | high",
      "type": "",
      "chapter_title": "",
      "description": "",
      "suggestion": ""
    }}
  ],
  "overall_suggestion": ""
}}
"""

CONSISTENCY_FIX_PROMPT = """你是一个论文和课程设计报告修订助手。

任务：根据一致性问题的描述和建议，修改相关章节正文，消除该问题。

Project Brief：{project_brief}
完整大纲：{outline}
问题类型：{issue_type}
严重程度：{severity}
问题描述：{description}
修改建议：{suggestion}
关联章节：{related_chapter}
章节正文：{chapter_drafts}

要求：
1. 只指出需要修改的章节，不要返回正文。
2. chapter_title 必须与「章节正文」中的章节标题一致；如果问题出在子标题，也要返回该子标题所属、已有正文的那一章。
3. 输出 JSON，不要输出 Markdown 代码块。

输出结构：
{{
  "chapter_updates": [
    {{
      "chapter_title": ""
    }}
  ],
  "fix_summary": ""
}}
"""

CONSISTENCY_FIX_CHAPTER_PROMPT = """你是一个论文和课程设计报告修订助手。

任务：按一致性问题的建议，修订当前这份章节草稿。只改与问题相关的内容，其余段落尽量保持原样。

问题类型：{issue_type}
严重程度：{severity}
问题描述：{description}
修改建议：{suggestion}
需要处理的标题：{target_titles}
当前章节标题：{chapter_title}
当前章节正文：
{chapter_content}

要求：
1. 输出修订后的完整 Markdown，不要输出 JSON，不要解释。
2. 保留原有标题层级。
3. 不得编造用户未提供的事实；缺失信息继续使用“[待补充：具体信息]”。
4. 保留已有 Markdown 表格、表题注、$$公式$$ 和行内 $公式$。
"""
