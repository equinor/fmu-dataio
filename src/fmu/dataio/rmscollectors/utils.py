from xtgeo import RoxUtils
import roxar
import roxar.jobs


def _get_project(project, readonly=True):
    """Get rms project

    Args:
        project (str or roxar.project): the project to return
        readonly (bool, optional): true is read only, defaults to true

    Returns:
        roxar.project: the loaded project
    """
    project = RoxUtils(project, readonly=readonly).project
    return project


def get_job(owner, job_type, job_name):
    """Get Roxar job

    Args:
        owner (list): list including parents of job
        job_type (str): what job type
        job_name (str): name of job

    Returns:
        dict: job settings
    """
    job = roxar.jobs.Job.get_job(
        owner=owner,
        type=job_type,
        name=job_name,
    )
    return job


def get_job_arguments(owner, job_type, job_name):
    """Get job arguments

    Args:
        owner (list): list including parents of job
        job_type (str): what job type
        job_name (str): name of job

    Returns:
        dict: job settings
    """
    job = get_job(owner, job_type, job_name)
    arguments = job.get_arguments()
    return arguments
