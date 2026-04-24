from celery import chain
from tasks.etl import copy_to_staging
from tasks.validator import validate_study
from tasks.db_check import check_study_not_imported
from tasks.importer import import_study
from tasks.docker_ops import restart_portal


def build_pipeline(source_dir: str, study_id: str):
    return chain(
        copy_to_staging.s(source_dir, study_id),
        validate_study.s(),
        check_study_not_imported.s(),
        import_study.s(),
        restart_portal.s(),
    )
