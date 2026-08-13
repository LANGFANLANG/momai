from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, User
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    @staticmethod
    def create_project(db: Session, payload: ProjectCreate, user: User | None = None) -> Project:
        project = Project(**payload.model_dump(), user_id=(user.id if user else "admin"))
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def list_projects(db: Session, user: User | None = None) -> list[Project]:
        statement = select(Project).order_by(Project.created_at.desc())
        if user is not None:
            statement = statement.where(Project.user_id == user.id)
        return list(db.scalars(statement))

    @staticmethod
    def get_project(db: Session, project_id: str, user: User | None = None) -> Project | None:
        project = db.get(Project, project_id)
        if project is not None and user is not None and project.user_id != user.id:
            return None
        return project

    @classmethod
    def get_project_or_404(cls, db: Session, project_id: str, user: User | None = None) -> Project:
        project = cls.get_project(db, project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    @classmethod
    def update_project(cls, db: Session, project_id: str, payload: ProjectUpdate, user: User | None = None) -> Project:
        project = cls.get_project_or_404(db, project_id, user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def delete_project(cls, db: Session, project_id: str, user: User | None = None) -> None:
        project = cls.get_project_or_404(db, project_id, user)
        db.delete(project)
        db.commit()
