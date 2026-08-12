from pydantic import BaseModel


class ProjectBriefGeneration(BaseModel):
    title_explanation: str | None = None
    background: str
    core_problem: str | None = None
    goal: str | None = None
    significance: str | None = None
    technical_route: str | None = None
    modules: list[str] = []
    expected_result: str | None = None
    writing_boundary: str | None = None
    missing_info: list[str] = []
    locked_facts: list[str] = []
