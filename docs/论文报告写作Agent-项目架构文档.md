# 论文报告写作 Agent Web 应用项目架构文档

## 1. 技术选型

本项目采用前后端分离架构。

前端使用 Vue3 + Vite，负责项目管理、信息填写、大纲编辑、章节关系编辑、章节写作和全文预览。后端使用 FastAPI，负责业务 API、数据库访问、文档导出和 AI 工作流调度。AI 写作流程使用 LangGraph 编排，把“Project Brief 生成、大纲生成、章节关系生成、章节正文生成、章节摘要生成、全文一致性检查”等任务拆成可维护的 graph。

推荐技术栈：

- 前端框架：Vue3 + Vite
- 前端语言：TypeScript
- 前端状态管理：Pinia
- 前端路由：Vue Router
- UI 样式：Tailwind CSS
- 编辑器：TipTap，MVP 可先使用 Markdown 编辑器
- 后端框架：FastAPI
- AI 编排：LangGraph
- LLM 调用：OpenAI API，或兼容 OpenAI SDK 的模型服务
- 数据库：PostgreSQL，MVP 可用 SQLite
- ORM：SQLAlchemy 2.0
- 数据校验：Pydantic v2
- 数据迁移：Alembic
- 异步任务：Celery + Redis，MVP 可先使用 FastAPI BackgroundTasks
- 文档导出：python-docx、markdown-it-py、可选 Pandoc
- 文件存储：本地文件系统，后续可换 S3 兼容存储
- 鉴权：JWT + Refresh Token

## 2. 系统架构

```text
Browser
  |
  | HTTP / SSE / WebSocket
  v
Vue3 + Vite Frontend
  |
  | REST API
  v
FastAPI Backend
  |
  |-- Project Service
  |-- Brief Service
  |-- Outline Service
  |-- Chapter Service
  |-- Review Service
  |-- Export Service
  |-- LangGraph Workflow Service
  |
  v
LangGraph Agent Workflows
  |
  |-- BriefGraph
  |-- OutlineGraph
  |-- RelationGraph
  |-- ChapterDraftGraph
  |-- ChapterSummaryGraph
  |-- ConsistencyReviewGraph
  |
  v
LLM Provider
  |
  |-- OpenAI API or compatible provider
  |
  v
Database / File Storage
```

## 3. 目录结构

```text
paper-agent-web/
  frontend/
    index.html
    package.json
    vite.config.ts
    tsconfig.json
    src/
      main.ts
      App.vue
      router/
        index.ts
      stores/
        project.ts
        chapter.ts
        generation.ts
      api/
        http.ts
        projects.ts
        brief.ts
        outline.ts
        relations.ts
        chapters.ts
        review.ts
        export.ts
        materials.ts
      pages/
        ProjectListPage.vue
        ProjectCreatePage.vue
        ProjectLayout.vue
        ProjectBriefPage.vue
        OutlinePage.vue
        ChapterRelationsPage.vue
        ChapterWritingPage.vue
        ConsistencyReviewPage.vue
        ExportPage.vue
      components/
        project/
        outline/
        chapter/
        editor/
        review/
        ui/
      types/
        project.ts
        chapter.ts
        generation.ts
      styles/
        index.css

  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
      api/
        deps.py
        routers/
          projects.py
          brief.py
          outline.py
          relations.py
          chapters.py
          review.py
          export.py
          materials.py
      db/
        session.py
        base.py
        models/
          user.py
          project.py
          project_context.py
          project_brief.py
          chapter.py
          chapter_relation.py
          chapter_draft.py
          chapter_summary.py
          material.py
          feedback.py
          consistency_issue.py
          export_record.py
        repositories/
      schemas/
        project.py
        brief.py
        outline.py
        chapter.py
        review.py
        export.py
      services/
        projects.py
        brief.py
        outline.py
        chapters.py
        review.py
        export.py
        materials.py
      ai/
        llm.py
        prompts.py
        states.py
        graphs/
          brief_graph.py
          outline_graph.py
          relation_graph.py
          chapter_draft_graph.py
          chapter_summary_graph.py
          consistency_review_graph.py
        nodes/
          load_context.py
          build_prompt.py
          call_model.py
          validate_output.py
          repair_output.py
          persist_result.py
      export/
        markdown.py
        docx.py
    alembic/
      versions/
    tests/
      unit/
      integration/

  docs/
  docker-compose.yml
  README.md
```

## 4. 前端页面架构

前端页面与产品流程一一对应。

```text
/projects
  项目列表页

/projects/new
  项目创建页

/projects/:projectId/brief
  关键信息填写与 Project Brief 确认页

/projects/:projectId/outline
  大纲生成与编辑页

/projects/:projectId/relations
  章节关系页

/projects/:projectId/chapters/:chapterId
  章节写作页

/projects/:projectId/review
  全文一致性检查页

/projects/:projectId/export
  全文预览与导出页
```

前端状态建议拆分：

- `projectStore`：项目基础信息、Project Context、Project Brief
- `chapterStore`：大纲、章节关系、章节草稿、章节摘要
- `generationStore`：AI 生成状态、流式输出、错误提示

章节生成建议支持 SSE 或 WebSocket，用户能看到正文逐步输出。MVP 如果想简单，也可以先使用普通 HTTP 请求，生成完成后一次性返回。

## 5. 后端核心模块

### 5.1 Project Service

职责：

- 创建项目
- 更新项目基础信息
- 查询项目进度
- 管理项目状态

项目状态：

- `drafting_info`：正在填写信息
- `brief_ready`：Project Brief 已生成
- `outline_ready`：大纲已确认
- `relations_ready`：章节关系已确认
- `drafting_chapters`：正在生成章节
- `review_ready`：可以进行全文检查
- `export_ready`：可以导出

### 5.2 Brief Service

职责：

- 保存用户填写的 Project Context。
- 调用 BriefGraph 生成 Project Brief。
- 标记缺失信息和锁定事实。

### 5.3 Outline Service

职责：

- 调用 OutlineGraph 生成大纲。
- 支持用户编辑、排序、删除和锁定章节。
- 为章节保存 purpose 和 suggested_word_count。

### 5.4 Chapter Relation Service

职责：

- 调用 RelationGraph 为每章生成章节关系。
- 维护每章的 previous_bridge、next_bridge、key_points、output_conclusions。
- 保证章节写作时前后关联。

### 5.5 Draft Service

职责：

- 调用 ChapterDraftGraph 生成章节草稿。
- 支持整章生成、续写、重写、扩写、压缩和润色。
- 保存每次草稿版本和 prompt_snapshot。

### 5.6 Summary Service

职责：

- 调用 ChapterSummaryGraph 对章节正文做上下文压缩。
- 保存章节摘要、关键结论、已使用事实和后续影响。

### 5.7 Consistency Review Service

职责：

- 调用 ConsistencyReviewGraph 检查全文一致性。
- 输出术语不统一、章节跳跃、事实冲突、重复内容等问题。

### 5.8 Export Service

职责：

- 合并章节正文。
- 导出 Markdown。
- 导出 Word。
- 后续支持 PDF 和 LaTeX。

## 6. 数据库表结构

数据库层使用 SQLAlchemy Models，接口层使用 Pydantic Schemas。下面用 Python 类型描述核心字段。

```python
class User:
    id: str
    email: str
    name: str | None
    created_at: datetime
    updated_at: datetime


class Project:
    id: str
    user_id: str
    type: ProjectType
    title: str
    major: str | None
    school: str | None
    target_word_count: int | None
    language: str
    requirements: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectContext:
    id: str
    project_id: str
    background: str | None
    problem: str | None
    goal: str | None
    scenario: str | None
    target_users: str | None
    methods: list[str] | None
    technologies: list[str] | None
    modules: list[str] | None
    architecture: str | None
    environment: str | None
    data_sources: list[str] | None
    experiments: str | None
    innovations: list[str] | None
    constraints: list[str] | None
    writing_prefs: dict | None
    created_at: datetime
    updated_at: datetime


class ProjectBrief:
    id: str
    project_id: str
    title_explanation: str | None
    background: str
    core_problem: str
    goal: str
    significance: str | None
    technical_route: str | None
    modules: list[str] | None
    expected_result: str | None
    writing_boundary: str | None
    missing_info: list[str] | None
    locked_facts: list[str] | None
    created_at: datetime
    updated_at: datetime


class Chapter:
    id: str
    project_id: str
    parent_id: str | None
    title: str
    level: int
    order: int
    purpose: str | None
    suggested_word_count: int | None
    status: ChapterStatus
    created_at: datetime
    updated_at: datetime


class ChapterRelation:
    id: str
    chapter_id: str
    previous_bridge: str | None
    next_bridge: str | None
    required_questions: list[str] | None
    depends_on_facts: list[str] | None
    key_points: list[str] | None
    output_conclusions: list[str] | None
    avoid_repeating: list[str] | None
    created_at: datetime
    updated_at: datetime


class ChapterDraft:
    id: str
    chapter_id: str
    version: int
    content: str
    prompt_snapshot: dict | None
    generation_mode: DraftMode
    created_at: datetime


class ChapterSummary:
    id: str
    chapter_id: str
    summary: str
    key_conclusions: list[str] | None
    used_facts: list[str] | None
    forward_implications: list[str] | None
    created_at: datetime
    updated_at: datetime


class Material:
    id: str
    project_id: str
    type: MaterialType
    title: str
    content: str | None
    file_url: str | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime


class FeedbackItem:
    id: str
    project_id: str
    chapter_id: str | None
    raw_text: str
    category: str | None
    status: FeedbackStatus
    suggestion: str | None
    created_at: datetime
    updated_at: datetime


class ConsistencyIssue:
    id: str
    project_id: str
    chapter_id: str | None
    severity: IssueSeverity
    type: str
    description: str
    suggestion: str | None
    status: IssueStatus
    created_at: datetime
    updated_at: datetime


class ExportRecord:
    id: str
    project_id: str
    format: ExportFormat
    file_url: str
    created_at: datetime
```

枚举类型：

```python
ProjectType = Literal["course_report", "thesis", "proposal"]
ProjectStatus = Literal[
    "drafting_info",
    "brief_ready",
    "outline_ready",
    "relations_ready",
    "drafting_chapters",
    "review_ready",
    "export_ready",
]
ChapterStatus = Literal["planned", "relation_ready", "drafting", "drafted", "reviewed"]
DraftMode = Literal["generate", "rewrite", "continue", "expand", "compress", "polish"]
MaterialType = Literal[
    "requirement",
    "code_summary",
    "database_schema",
    "experiment_data",
    "reference",
    "advisor_feedback",
    "template",
    "other",
]
FeedbackStatus = Literal["open", "applied", "ignored"]
IssueSeverity = Literal["low", "medium", "high"]
IssueStatus = Literal["open", "fixed", "ignored"]
ExportFormat = Literal["markdown", "docx", "pdf", "latex"]
```

## 7. API 设计

### 7.1 项目 API

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

### 7.2 Project Brief API

```text
POST  /api/projects/{project_id}/context
POST  /api/projects/{project_id}/brief/generate
PATCH /api/projects/{project_id}/brief
```

Brief 生成请求：

```json
{
  "project_id": "project_id"
}
```

返回：

```json
{
  "brief": {
    "background": "...",
    "core_problem": "...",
    "goal": "...",
    "technical_route": "...",
    "missing_info": []
  }
}
```

### 7.3 大纲 API

```text
POST  /api/projects/{project_id}/outline/generate
GET   /api/projects/{project_id}/chapters
PATCH /api/projects/{project_id}/chapters
```

请求：

```json
{
  "outline_preference": "engineering_focused"
}
```

返回：

```json
{
  "chapters": [
    {
      "id": "chapter_id",
      "title": "绪论",
      "level": 1,
      "order": 1,
      "purpose": "说明研究背景、意义和主要内容",
      "suggested_word_count": 1500
    }
  ]
}
```

### 7.4 章节关系 API

```text
POST  /api/projects/{project_id}/relations/generate
GET   /api/projects/{project_id}/relations
PATCH /api/chapters/{chapter_id}/relation
```

返回：

```json
{
  "relations": [
    {
      "chapter_id": "chapter_id",
      "previous_bridge": "承接绪论中提出的研究背景和问题。",
      "next_bridge": "为后续系统设计提供需求依据。",
      "key_points": ["功能需求", "非功能需求", "用户角色"],
      "output_conclusions": ["明确系统应包含的核心功能模块"]
    }
  ]
}
```

### 7.5 章节生成 API

```text
POST /api/chapters/{chapter_id}/drafts/generate
POST /api/chapters/{chapter_id}/summary/generate
GET  /api/chapters/{chapter_id}/drafts
```

章节生成请求：

```json
{
  "mode": "generate",
  "user_instruction": "增加工程实现细节"
}
```

章节生成返回：

```json
{
  "draft_id": "draft_id",
  "content": "..."
}
```

如果使用 SSE，接口可以设计为：

```text
GET /api/chapters/{chapter_id}/drafts/stream?mode=generate
```

事件类型：

```text
token
done
error
```

### 7.6 全文检查 API

```text
POST /api/projects/{project_id}/review/consistency
GET  /api/projects/{project_id}/review/issues
PATCH /api/review/issues/{issue_id}
```

返回：

```json
{
  "issues": [
    {
      "severity": "medium",
      "type": "term_inconsistency",
      "description": "第二章使用“用户端”，第四章使用“前台用户”，建议统一。",
      "suggestion": "全文统一为“普通用户端”。"
    }
  ]
}
```

### 7.7 导出 API

```text
POST /api/projects/{project_id}/export/markdown
POST /api/projects/{project_id}/export/docx
GET  /api/exports/{export_id}/download
```

## 8. LangGraph AI 编排

LangGraph Workflow Service 负责将写作任务拆成可追踪、可校验、可重试的 graph。每个 graph 由加载上下文、构建 prompt、调用模型、校验输出、持久化结果等节点组成。

核心流程：

```text
用户操作
  |
  v
FastAPI Router
  |
  v
Service Layer
  |
  v
LangGraph Workflow
  |
  |-- load_context
  |-- build_prompt
  |-- call_model
  |-- validate_output
  |-- repair_output, optional
  |-- persist_result
  |
  v
返回结果
```

### 8.1 Graph 划分

```text
BriefGraph
  load_project_context -> build_brief_prompt -> call_model -> validate_brief_json -> save_brief

OutlineGraph
  load_brief -> build_outline_prompt -> call_model -> validate_outline_json -> save_chapters

RelationGraph
  load_brief_and_outline -> build_relation_prompt -> call_model -> validate_relations_json -> save_relations

ChapterDraftGraph
  load_generation_context -> build_chapter_prompt -> call_model -> save_draft -> summarize_chapter

ChapterSummaryGraph
  load_latest_draft -> build_summary_prompt -> call_model -> validate_summary_json -> save_summary

ConsistencyReviewGraph
  load_full_project -> build_review_prompt -> call_model -> validate_issues_json -> save_issues
```

### 8.2 LangGraph 状态结构

```python
class GenerationState(TypedDict, total=False):
    project_id: str
    chapter_id: str | None
    mode: str | None
    user_instruction: str | None
    project: dict
    context: dict
    brief: dict
    outline: list[dict]
    current_chapter: dict
    current_relation: dict
    previous_summaries: list[dict]
    related_materials: list[dict]
    prompt: str
    raw_output: str
    parsed_output: dict
    errors: list[str]
```

### 8.3 节点职责

```text
load_context：
从数据库加载 Project、ProjectContext、ProjectBrief、Chapter、Relation、Summary、Material 等数据。

build_prompt：
根据任务类型选择 prompt 模板，并填充上下文。

call_model：
调用 OpenAI API 或兼容模型服务，拿到模型输出。

validate_output：
使用 Pydantic Schema 校验 JSON 输出。校验失败时可进入 repair_output 节点。

repair_output：
当模型返回非 JSON 或字段缺失时，尝试修复为合法结构。

persist_result：
将结构化结果写入数据库，如 Brief、Chapter、Relation、Draft、Summary、Issue。
```

### 8.4 Graph 示例

```python
from langgraph.graph import StateGraph, END


def build_brief_graph():
    graph = StateGraph(GenerationState)
    graph.add_node("load_context", load_context)
    graph.add_node("build_prompt", build_brief_prompt)
    graph.add_node("call_model", call_model)
    graph.add_node("validate_output", validate_brief_output)
    graph.add_node("persist_result", save_brief)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "build_prompt")
    graph.add_edge("build_prompt", "call_model")
    graph.add_edge("call_model", "validate_output")
    graph.add_edge("validate_output", "persist_result")
    graph.add_edge("persist_result", END)

    return graph.compile()
```

### 8.5 章节流式生成

章节正文适合使用 SSE 或 WebSocket 流式返回。

```text
Vue 页面发起生成请求
  |
  v
FastAPI 创建生成任务
  |
  v
LangGraph 执行 ChapterDraftGraph
  |
  v
通过 SSE 或 WebSocket 返回 token
  |
  v
生成完成后保存 ChapterDraft 和 ChapterSummary
```

## 9. 生成上下文策略

章节正文生成时应包含：

- Project 基础信息
- Project Brief
- 完整一级大纲
- 当前章节及其小节
- 当前章节关系
- 所有前序章节摘要
- 上一章摘要和关键结论
- 相关材料
- 用户额外要求

默认不包含：

- 所有前序章节全文
- 无关材料
- 未确认的大纲版本

相关材料选择策略：

- 如果材料绑定到当前章节，优先使用。
- `requirement` 可用于需求分析章节。
- `database_schema` 可用于系统设计和系统实现章节。
- `experiment_data` 可用于测试分析章节。
- `reference` 可用于绪论和相关理论章节。

## 10. 主要 Prompt 模板

以下模板为业务核心，可放入 `backend/app/ai/prompts.py`。

### 10.1 Project Brief 生成 Prompt

```text
你是一个课程设计报告和本科论文写作规划助手。

任务：
根据用户填写的信息，整理一份结构化 Project Brief，作为后续生成大纲和章节正文的唯一事实来源。

写作类型：
{{project.type}}

项目标题：
{{project.title}}

用户填写的信息：
{{project_context}}

要求：
1. 只使用用户已提供的信息。
2. 不得编造实验结果、功能模块、真实参考文献或学校要求。
3. 如果信息缺失，请放入 missing_info。
4. 表述要正式、清晰，适合作为论文或课程设计报告的写作依据。
5. 输出 JSON，不要输出 Markdown。

输出结构：
{
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
}
```

### 10.2 大纲生成 Prompt

```text
你是一个本科论文和课程设计报告大纲设计助手。

任务：
根据 Project Brief 为用户生成结构合理、前后递进的大纲。

写作类型：
{{project.type}}

目标字数：
{{project.target_word_count}}

学校或教师要求：
{{project.requirements}}

Project Brief：
{{project_brief}}

要求：
1. 大纲必须符合写作类型。
2. 章节顺序要体现逻辑递进。
3. 工程类项目应包含需求分析、系统设计、系统实现、测试分析。
4. 本科论文应包含绪论、相关理论或技术基础、主体设计或实验、总结展望。
5. 不要生成用户事实之外的新功能或实验。
6. 为每个章节给出 purpose 和 suggested_word_count。
7. 输出 JSON，不要输出 Markdown。

输出结构：
{
  "chapters": [
    {
      "title": "",
      "level": 1,
      "order": 1,
      "purpose": "",
      "suggested_word_count": 1200,
      "children": []
    }
  ]
}
```

### 10.3 章节关系生成 Prompt

```text
你是一个论文结构规划助手，擅长建立章节之间的承接关系。

任务：
根据 Project Brief 和已确认大纲，为每个一级章节生成章节关系说明。

Project Brief：
{{project_brief}}

完整大纲：
{{outline}}

要求：
1. 每章都必须说明本章目的。
2. 每章都必须说明如何承接上一章。
3. 每章都必须说明如何引出下一章。
4. 每章都必须列出依赖的项目事实。
5. 每章都必须列出输出结论。
6. 避免不同章节重复写同一内容。
7. 第一章 previous_bridge 可以说明从研究背景切入。
8. 最后一章 next_bridge 可以说明收束全文并展望后续。
9. 输出 JSON，不要输出 Markdown。

输出结构：
{
  "relations": [
    {
      "chapter_title": "",
      "purpose": "",
      "previous_bridge": "",
      "next_bridge": "",
      "required_questions": [],
      "depends_on_facts": [],
      "key_points": [],
      "output_conclusions": [],
      "avoid_repeating": []
    }
  ]
}
```

### 10.4 章节正文生成 Prompt

```text
你是一个本科论文和课程设计报告初稿写作助手。

任务：
根据当前章节目标和上下文，生成当前章节正文初稿。

写作类型：
{{project.type}}

项目标题：
{{project.title}}

Project Brief：
{{project_brief}}

完整大纲：
{{outline}}

已完成章节摘要：
{{previous_summaries}}

当前章节：
{{current_chapter}}

当前章节关系：
{{current_relation}}

相关用户材料：
{{related_materials}}

用户额外要求：
{{user_instruction}}

写作要求：
1. 只写当前章节，不要写其他章节。
2. 当前章节必须承接 previous_bridge，并为 next_bridge 做铺垫。
3. 必须覆盖 key_points。
4. 必须围绕 output_conclusions 收束。
5. 不得编造用户未提供的实验结果、功能模块、数据或真实参考文献。
6. 如果需要但缺失的信息，请使用“[待补充：具体信息]”标记。
7. 避免重复已完成章节已经充分说明的内容。
8. 语言应正式、清晰，符合本科论文或课程设计报告初稿风格。
9. 输出 Markdown。
```

### 10.5 章节摘要生成 Prompt

```text
你是一个论文上下文压缩助手。

任务：
阅读当前章节正文，生成供后续章节使用的结构化摘要。

章节标题：
{{chapter.title}}

章节正文：
{{chapter_draft.content}}

要求：
1. 摘要应简洁，保留对后文有用的信息。
2. 提取本章关键结论。
3. 提取本章已经使用过的项目事实。
4. 说明本章对后续章节的影响。
5. 输出 JSON，不要输出 Markdown。

输出结构：
{
  "summary": "",
  "key_conclusions": [],
  "used_facts": [],
  "forward_implications": []
}
```

### 10.6 全文一致性检查 Prompt

```text
你是一个论文和课程设计报告审稿助手。

任务：
检查全文初稿在结构、事实、术语和章节衔接上的一致性。

Project Brief：
{{project_brief}}

完整大纲：
{{outline}}

章节关系：
{{relations}}

章节正文：
{{chapter_drafts}}

检查要求：
1. 检查章节标题与正文是否匹配。
2. 检查章节之间是否存在逻辑跳跃。
3. 检查技术名词、模块名称、研究对象是否统一。
4. 检查是否出现 Project Brief 中没有的事实。
5. 检查是否重复大段描述同一内容。
6. 检查摘要、绪论、总结之间是否呼应。
7. 检查是否有章节明显过短、过长或偏题。
8. 输出问题列表和修改建议。
9. 输出 JSON，不要输出 Markdown。

输出结构：
{
  "issues": [
    {
      "severity": "low | medium | high",
      "type": "",
      "chapter_title": "",
      "description": "",
      "suggestion": ""
    }
  ],
  "overall_suggestion": ""
}
```

### 10.7 段落重写 Prompt

```text
你是一个论文段落修改助手。

任务：
根据用户要求重写选中段落，并保持其与当前章节和全文上下文一致。

Project Brief：
{{project_brief}}

当前章节：
{{current_chapter}}

当前章节关系：
{{current_relation}}

原段落：
{{selected_text}}

用户修改要求：
{{user_instruction}}

要求：
1. 只输出重写后的段落。
2. 不改变事实含义。
3. 不新增用户未提供的信息。
4. 保持正式、自然的论文或报告表达。
5. 避免空泛套话。
```

## 11. 文档导出设计

### 11.1 Markdown 导出

流程：

1. 读取项目标题。
2. 按章节 `order` 排序。
3. 将章节标题转换为 Markdown 标题。
4. 合并最新草稿。
5. 添加参考文献或待补充区。
6. 输出 `.md` 文件。

### 11.2 Word 导出

流程：

1. 创建 docx 文档。
2. 添加封面信息，可选。
3. 添加标题、摘要、关键词，可选。
4. 按章节层级写入标题和正文。
5. 应用基础样式。
6. 添加参考文献。
7. 保存 `.docx` 文件。

MVP 可先实现基础 Word 样式：

- 一级标题：黑体，小三，居中或左对齐。
- 二级标题：黑体，四号。
- 正文：宋体，小四，1.5 倍行距。
- 段首缩进两个中文字符。

## 12. 错误处理

### 12.1 AI 输出不是合法 JSON

处理：

- LangGraph 进入 `repair_output` 节点，尝试将输出修复为合法 JSON。
- 修复失败时提示用户重试。
- 记录原始输出、prompt_snapshot 和错误信息。

### 12.2 用户信息不足

处理：

- Brief 阶段将缺失信息写入 `missing_info`。
- 大纲可继续生成。
- 章节正文中使用 `[待补充：...]` 标记缺失内容。
- 页面提示用户补充关键字段。

### 12.3 章节生成失败

处理：

- 保留用户当前编辑内容。
- 允许重试。
- 不覆盖已有草稿。
- 记录失败原因。

### 12.4 前后文冲突

处理：

- Consistency Review 输出冲突位置和建议。
- 不自动覆盖正文，除非用户确认。

## 13. 权限与数据安全

MVP 至少需要：

- 用户只能访问自己的项目。
- 上传材料限制文件大小。
- AI prompt 中不传递其他用户数据。
- 导出文件带用户项目权限。
- 删除项目时同时删除相关草稿和导出记录。
- 后端 API 校验 `project_id` 是否属于当前用户。

后续可增加：

- 项目分享
- 只读协作
- 操作审计日志

## 14. 测试计划

### 14.1 前端测试

- 项目创建表单
- 大纲拖拽排序
- 章节关系编辑
- 章节写作页面状态
- SSE 或 WebSocket 流式输出

### 14.2 后端单元测试

- Prompt 输入组装
- Pydantic 输出校验
- LangGraph 节点状态流转
- 大纲排序
- 章节层级处理
- Markdown 导出
- Word 导出

### 14.3 后端集成测试

- 创建项目到生成 Brief
- Brief 到大纲生成
- 大纲到章节关系生成
- 章节生成到摘要保存
- 全文检查到问题保存

### 14.4 端到端测试

核心路径：

1. 创建本科论文项目。
2. 填写关键信息。
3. 生成并确认 Brief。
4. 生成大纲。
5. 生成章节关系。
6. 生成第一章正文。
7. 生成第一章摘要。
8. 导出 Markdown。

## 15. 开发里程碑

### Milestone 1：项目基础

- Vue3 + Vite 前端初始化
- FastAPI 后端初始化
- SQLAlchemy 数据模型
- Alembic 数据迁移
- 用户登录
- 项目创建与列表

### Milestone 2：写作上下文

- 项目信息表单
- Project Brief 生成
- Brief 编辑与锁定事实
- BriefGraph 实现

### Milestone 3：大纲和章节关系

- 大纲生成
- 大纲编辑
- OutlineGraph 实现
- 章节关系生成
- 章节关系编辑
- RelationGraph 实现

### Milestone 4：章节写作

- 章节编辑器
- 章节正文生成
- 段落重写
- 章节摘要生成
- ChapterDraftGraph 和 ChapterSummaryGraph 实现

### Milestone 5：检查与导出

- 全文一致性检查
- ConsistencyReviewGraph 实现
- Markdown 导出
- Word 导出

## 16. 后续扩展

可在 MVP 稳定后增加：

- 文献检索和引用管理
- Zotero 集成
- 代码仓库分析
- 学校 Word 模板解析
- 答辩 PPT 自动生成
- 多版本对比
- 导师批注工作流
- 团队课程报告模板库
