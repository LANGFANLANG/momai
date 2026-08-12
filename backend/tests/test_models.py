from app.db.models import Project


def test_project_defaults_to_drafting_info(db_session):
    project = Project(type="thesis", title="LifePilot paper", language="zh")
    db_session.add(project)
    db_session.flush()

    assert project.status == "drafting_info"
    assert project.user_id == "local-dev-user"
