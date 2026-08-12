from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    @staticmethod
    def create_project(db: Session, payload: ProjectCreate) -> Project:
        project = Project(**payload.model_dump())
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def list_projects(db: Session) -> list[Project]:
        return list(db.scalars(select(Project).order_by(Project.created_at.desc())))

    @staticmethod
    def get_project(db: Session, project_id: str) -> Project | None:
        return db.get(Project, project_id)

    @classmethod
    def get_project_or_404(cls, db: Session, project_id: str) -> Project:
        project = cls.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    @classmethod
    def update_project(cls, db: Session, project_id: str, payload: ProjectUpdate) -> Project:
        project = cls.get_project_or_404(db, project_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def delete_project(cls, db: Session, project_id: str) -> None:
        project = cls.get_project_or_404(db, project_id)
        db.delete(project)
        db.commit()
