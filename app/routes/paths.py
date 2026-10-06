"""Screens for one career path: level check, personalised plan, overview, resources,
projects, progress and proof."""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..services import assessment, catalog

paths_bp = Blueprint('paths', __name__, url_prefix='/path/<int:path_id>')


def _path_or_404(path_id: int):
    path = catalog.get_path(path_id)
    if path is None:
        abort(404)
    return path


def _level():
    """Level from the URL. Missing or unknown = None (show all levels)."""
    level = request.args.get('level')
    return level if level in catalog.LEVELS else None


@paths_bp.get('/assess')
def assess(path_id):
    path = _path_or_404(path_id)
    return render_template('assess.html', path=path, level=None, questions=assessment.get_questions(path_id),
                           source=request.args.get('source', ''))


@paths_bp.post('/assess')
def assess_submit(path_id):
    _path_or_404(path_id)
    questions = assessment.get_questions(path_id)
    answers = {q['slug']: request.form.get(q['slug'], '') for q in questions}
    result = assessment.score_answers(questions, answers)
    return redirect(url_for('paths.plan', path_id=path_id, level=result['level'], score=result['score'],
                            missed=','.join(result['missed']) or None))


@paths_bp.get('/plan')
def plan(path_id):
    path = _path_or_404(path_id)
    level = _level()
    if level is None:
        return redirect(url_for('paths.assess', path_id=path_id))

    score = request.args.get('score', '')
    total = len(assessment.get_questions(path_id))
    score = int(score) if score.isdigit() and int(score) <= total else None
    missed = [slug for slug in request.args.get('missed', '').split(',') if slug]
    guide = assessment.build_start_guide(path_id, level, missed)
    return render_template('plan.html', path=path, level=level, score=score, total=total, **guide)


@paths_bp.get('')
def path_detail(path_id):
    path = _path_or_404(path_id)
    return render_template('recommended_path.html', path=path, level=_level(),
                           source=request.args.get('source', ''), **catalog.get_path_stats(path_id))


@paths_bp.get('/resources')
def resources(path_id):
    path = _path_or_404(path_id)
    items = catalog.list_resources(
        path_id,
        level=_level(),
        resource_type=request.args.get('type'),
        verified_only=request.args.get('verified_only') == '1',
        free_cert_only=request.args.get('free_cert_only') == '1',
    )
    return render_template('resources.html', path=path, level=_level(), resources=items,
                           resource_types=catalog.RESOURCE_TYPES)


@paths_bp.get('/projects')
def projects(path_id):
    path = _path_or_404(path_id)
    return render_template('projects.html', path=path, level=_level(),
                           projects=catalog.list_projects(path_id, _level()))


@paths_bp.get('/progress')
def progress(path_id):
    path = _path_or_404(path_id)
    return render_template('progress.html', path=path, level=_level(),
                           projects=catalog.list_projects(path_id))


@paths_bp.get('/proof')
def proof(path_id):
    path = _path_or_404(path_id)
    return render_template('cv.html', path=path, level=_level(),
                           projects=catalog.list_projects(path_id))
