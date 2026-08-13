from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Material, ProjectBrief, ProjectContext
from app.schemas.codebase import CodebaseAnalysisRead, CodebaseFactRead, FileTreeSummary
from app.services.projects import ProjectService


IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "logs",
    "node_modules",
    "target",
    "venv",
}
SENSITIVE_NAMES = {".env", ".env.local", "credentials.json", "token.json"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
TEXT_SUFFIXES = {
    ".c",
    ".conf",
    ".cs",
    ".css",
    ".go",
    ".gradle",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".php",
    ".properties",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}
KEY_FILE_NAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "build.gradle",
    "docker-compose.yml",
    "application.yml",
    "application.yaml",
    "README.md",
}


@dataclass
class AppliedCodebaseAnalysis:
    material: Material | None
    brief_updated: bool
    context_updated: bool
    locked_facts_added: int


def _as_posix(path: Path) -> str:
    return path.as_posix()


def _safe_read(path: Path, max_chars: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


class CodebaseAnalysisService:
    @classmethod
    def analyze_path(
        cls,
        root_path: str | Path,
        *,
        project_title: str | None = None,
        user_hint: str | None = None,
        include_tests: bool = False,
        include_docs: bool = True,
        max_files: int = 120,
    ) -> CodebaseAnalysisRead:
        root = Path(root_path).expanduser()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(str(root))

        file_tree = cls._scan_files(root, include_tests, include_docs, max_files)
        files = [root / item for item in file_tree.included_files]
        contents = {item: _safe_read(root / item) for item in file_tree.included_files}
        tech_stack = cls._detect_tech_stack(contents)
        facts = cls._build_facts(contents, tech_stack)
        summary = cls._summary(project_title, user_hint, tech_stack, facts)
        missing = []
        if not any(fact.category == "database" for fact in facts):
            missing.append("未在当前项目中发现明确的数据库表结构或 migration 文件。")
        if not any(fact.category == "api" for fact in facts):
            missing.append("未在当前项目中发现明确的接口入口文件。")
        warnings = []
        if file_tree.total_files > len(files):
            warnings.append(f"项目文件较多，本次按预算选取了 {len(files)} 个关键文件。")
        return CodebaseAnalysisRead(
            summary=summary,
            tech_stack=tech_stack,
            file_tree=file_tree,
            facts=facts,
            missing_info=missing,
            warnings=warnings,
        )

    @classmethod
    def apply_to_project(
        cls,
        db: Session,
        project_id: str,
        analysis: CodebaseAnalysisRead,
        *,
        update_project_context: bool = True,
        update_project_brief: bool = True,
        create_material: bool = True,
    ) -> AppliedCodebaseAnalysis:
        project = ProjectService.get_project_or_404(db, project_id)
        material = None
        if create_material:
            material = Material(
                project_id=project.id,
                type="code_summary",
                title="本地项目分析报告",
                content=cls.to_markdown(analysis),
                metadata_={
                    "root_path": analysis.file_tree.root,
                    "fact_count": len(analysis.facts),
                },
            )
            db.add(material)

        context_updated = False
        if update_project_context:
            context = project.context or ProjectContext(project_id=project.id)
            context.technologies = cls._flatten_stack(analysis.tech_stack)
            context.modules = cls._fact_titles(analysis, {"module", "workflow"})
            context.architecture = cls._architecture_text(analysis)
            context.environment = cls._environment_text(analysis)
            db.add(context)
            context_updated = True

        brief_updated = False
        added = 0
        if update_project_brief:
            brief = project.brief or ProjectBrief(project_id=project.id)
            stack = cls._flatten_stack(analysis.tech_stack)
            modules = cls._fact_titles(
                analysis,
                {"module", "workflow", "frontend", "backend", "api", "database"},
            )
            brief.technical_route = cls._architecture_text(analysis)
            brief.modules = _unique([*(brief.modules or []), *modules])
            locked = _unique([*(brief.locked_facts or []), *stack, *modules])
            added = len(locked) - len(brief.locked_facts or [])
            brief.locked_facts = locked
            brief.missing_info = _unique([*(brief.missing_info or []), *analysis.missing_info])
            if not brief.background:
                brief.background = f"围绕《{project.title}》的真实本地项目代码展开分析与论文写作。"
            if not brief.core_problem:
                brief.core_problem = "将本地项目的技术架构、功能模块和实现流程整理为规范论文内容。"
            if not brief.goal:
                brief.goal = "基于项目源码完成系统分析、设计、实现与测试章节写作。"
            db.add(brief)
            brief_updated = True

        db.commit()
        if material is not None:
            db.refresh(material)
        return AppliedCodebaseAnalysis(material, brief_updated, context_updated, added)

    @staticmethod
    def to_markdown(analysis: CodebaseAnalysisRead) -> str:
        lines = ["# 本地项目分析报告", "", analysis.summary, "", "## 技术栈"]
        for group, items in analysis.tech_stack.items():
            if items:
                lines.append(f"- {group}: {'、'.join(items)}")
        lines.extend(["", "## 项目事实"])
        for fact in analysis.facts:
            evidence = "、".join(fact.evidence_files)
            lines.append(f"- **{fact.title}**：{fact.content}（证据：{evidence}）")
        if analysis.missing_info:
            lines.extend(["", "## 待补充信息"])
            lines.extend(f"- {item}" for item in analysis.missing_info)
        if analysis.warnings:
            lines.extend(["", "## 扫描提示"])
            lines.extend(f"- {item}" for item in analysis.warnings)
        return "\n".join(lines) + "\n"

    @classmethod
    def _scan_files(
        cls, root: Path, include_tests: bool, include_docs: bool, max_files: int
    ) -> FileTreeSummary:
        included: list[str] = []
        ignored: dict[str, int] = {}
        total = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            total += 1
            relative = path.relative_to(root)
            parts = set(relative.parts)
            ignored_dir = next((part for part in relative.parts if part in IGNORED_DIRS), None)
            if ignored_dir:
                ignored[ignored_dir] = ignored.get(ignored_dir, 0) + 1
                continue
            if not include_tests and any("test" in part.lower() for part in parts):
                ignored["tests"] = ignored.get("tests", 0) + 1
                continue
            if not include_docs and path.suffix.lower() == ".md":
                ignored["docs"] = ignored.get("docs", 0) + 1
                continue
            if path.name in SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
                ignored["sensitive"] = ignored.get("sensitive", 0) + 1
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in KEY_FILE_NAMES:
                ignored["binary_or_unknown"] = ignored.get("binary_or_unknown", 0) + 1
                continue
            included.append(_as_posix(relative))
        included.sort(key=cls._file_priority)
        return FileTreeSummary(
            root=str(root),
            total_files=total,
            included_files=included[:max_files],
            ignored_summary=ignored,
        )

    @staticmethod
    def _file_priority(path: str) -> tuple[int, str]:
        name = Path(path).name
        if name in KEY_FILE_NAMES:
            return (0, path)
        lowered = path.lower()
        if any(token in lowered for token in ("controller", "router", "api", "schema.sql")):
            return (1, path)
        if any(token in lowered for token in ("service", "mapper", "repository", "model", "entity")):
            return (2, path)
        if any(token in lowered for token in ("page", "view", "store")):
            return (3, path)
        return (9, path)

    @classmethod
    def _detect_tech_stack(cls, contents: dict[str, str]) -> dict[str, list[str]]:
        stack = {
            "frontend": [],
            "backend": [],
            "database": [],
            "middleware": [],
            "deployment": [],
        }
        joined = "\n".join(contents.values()).lower()
        package = contents.get("frontend/package.json") or next(
            (value for path, value in contents.items() if path.endswith("package.json")),
            "",
        )
        package_lower = package.lower()
        if '"vue"' in package_lower or "vue" in package_lower:
            stack["frontend"].append("Vue3")
        if "react" in package_lower:
            stack["frontend"].append("React")
        if "vite" in package_lower:
            stack["frontend"].append("Vite")
        if "pinia" in package_lower:
            stack["frontend"].append("Pinia")
        if "fastapi" in joined:
            stack["backend"].append("FastAPI")
        if "spring-boot" in joined or "springframework.boot" in joined:
            stack["backend"].append("Spring Boot")
        if "mybatis" in joined:
            stack["backend"].append("MyBatis")
        if "sqlalchemy" in joined:
            stack["backend"].append("SQLAlchemy")
        if "mysql" in joined:
            stack["database"].append("MySQL")
        if "postgres" in joined or "postgresql" in joined:
            stack["database"].append("PostgreSQL")
        if "sqlite" in joined or any(path.endswith(".sql") for path in contents):
            stack["database"].append("SQLite")
        if "redis" in joined:
            stack["middleware"].append("Redis")
        if "docker-compose" in "\n".join(contents.keys()).lower():
            stack["deployment"].append("Docker Compose")
        return {key: _unique(value) for key, value in stack.items()}

    @classmethod
    def _build_facts(
        cls, contents: dict[str, str], tech_stack: dict[str, list[str]]
    ) -> list[CodebaseFactRead]:
        facts: list[CodebaseFactRead] = []
        stack_items = cls._flatten_stack(tech_stack)
        if stack_items:
            facts.append(
                CodebaseFactRead(
                    category="tech_stack",
                    title="项目技术栈",
                    content=f"项目使用 {'、'.join(stack_items)} 等技术构建。",
                    evidence_files=cls._evidence_for_stack(contents),
                    confidence="high",
                    chapter_tags=["相关技术基础", "系统设计"],
                )
            )
        for path, text in contents.items():
            lowered = path.lower()
            if any(token in lowered for token in ("controller", "router", "api")) or "@app." in text:
                facts.append(cls._api_fact(path, text))
            if path.endswith(".sql") or "create table" in text.lower():
                facts.append(cls._database_fact(path, text))
            if any(token in lowered for token in ("service", "mapper", "repository")):
                facts.append(cls._module_fact(path, text))
            if path.endswith(".vue") or "/src/" in path and any(token in lowered for token in ("page", "view")):
                facts.append(cls._frontend_fact(path))
        return facts[:40]

    @staticmethod
    def _api_fact(path: str, text: str) -> CodebaseFactRead:
        routes = re.findall(r"['\"](/api/[^'\"]+|/[^'\"]+)['\"]", text)
        route_text = f"包含接口路径 {', '.join(_unique(routes)[:5])}。" if routes else "包含接口或路由入口。"
        return CodebaseFactRead(
            category="api",
            title=f"接口入口：{Path(path).name}",
            content=f"{Path(path).name} {route_text}",
            evidence_files=[path],
            confidence="medium",
            chapter_tags=["系统设计", "系统实现", "测试分析"],
        )

    @staticmethod
    def _database_fact(path: str, text: str) -> CodebaseFactRead:
        tables = re.findall(r"create\s+table\s+[`\"]?(\w+)", text, flags=re.IGNORECASE)
        table_text = f"定义了 {'、'.join(_unique(tables))} 等数据表。" if tables else "包含数据库结构定义。"
        return CodebaseFactRead(
            category="database",
            title="数据库结构",
            content=table_text,
            evidence_files=[path],
            confidence="high",
            chapter_tags=["系统设计", "系统实现"],
        )

    @staticmethod
    def _module_fact(path: str, text: str) -> CodebaseFactRead:
        names = re.findall(r"class\s+(\w+)|def\s+(\w+)\(", text)
        labels = [first or second for first, second in names]
        label_text = f"包含 {', '.join(labels[:5])} 等业务实现。" if labels else "包含业务逻辑实现。"
        return CodebaseFactRead(
            category="module",
            title=f"业务模块：{Path(path).stem}",
            content=label_text,
            evidence_files=[path],
            confidence="medium",
            chapter_tags=["需求分析", "系统设计", "系统实现"],
        )

    @staticmethod
    def _frontend_fact(path: str) -> CodebaseFactRead:
        return CodebaseFactRead(
            category="frontend",
            title=f"前端页面：{Path(path).stem}",
            content=f"{Path(path).name} 可作为前端交互界面或页面实现依据。",
            evidence_files=[path],
            confidence="medium",
            chapter_tags=["系统设计", "系统实现"],
        )

    @staticmethod
    def _evidence_for_stack(contents: dict[str, str]) -> list[str]:
        return [
            path
            for path in contents
            if Path(path).name in KEY_FILE_NAMES or path.endswith(".sql")
        ][:8]

    @staticmethod
    def _summary(
        project_title: str | None,
        user_hint: str | None,
        tech_stack: dict[str, list[str]],
        facts: list[CodebaseFactRead],
    ) -> str:
        title = project_title or "当前项目"
        stack = "、".join(CodebaseAnalysisService._flatten_stack(tech_stack)) or "未明确识别技术栈"
        modules = "、".join(fact.title for fact in facts if fact.category in {"module", "api"}) or "核心模块待补充"
        hint = f"用户提示：{user_hint}。" if user_hint else ""
        return f"《{title}》本地项目分析完成。{hint}项目主要使用 {stack}，可写入论文的核心依据包括 {modules}。"

    @staticmethod
    def _flatten_stack(tech_stack: dict[str, list[str]]) -> list[str]:
        items: list[str] = []
        for values in tech_stack.values():
            items.extend(values)
        return _unique(items)

    @staticmethod
    def _fact_titles(analysis: CodebaseAnalysisRead, categories: set[str]) -> list[str]:
        return _unique([fact.title for fact in analysis.facts if fact.category in categories])

    @staticmethod
    def _architecture_text(analysis: CodebaseAnalysisRead) -> str:
        stack = "、".join(CodebaseAnalysisService._flatten_stack(analysis.tech_stack))
        facts = "；".join(f"{fact.title}：{fact.content}" for fact in analysis.facts[:8])
        return f"系统基于本地项目分析结果整理，技术栈包括 {stack}。主要结构包括：{facts}"

    @staticmethod
    def _environment_text(analysis: CodebaseAnalysisRead) -> str:
        return f"项目根目录：{analysis.file_tree.root}；扫描文件数：{len(analysis.file_tree.included_files)}。"
