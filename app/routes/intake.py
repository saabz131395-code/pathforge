"""Screen 1: choose a path, or take the quick-match quiz.

After a path is chosen, the learner goes to that path's level check.
State travels only in the URL (no sessions). Every POST redirects (Post/Redirect/Get).
"""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from ..services import catalog
from ..services.home import load_home_content
from ..services.recommendation import QUIZ, score_quiz

intake_bp = Blueprint('intake', __name__)


@intake_bp.get('/')
def home():
    return render_template('intake.html', paths=catalog.list_active_paths(), home=load_home_content())


@intake_bp.post('/recommend')
def recommend():
    interest = request.form.get('interest', '')
    if interest == 'not_sure':
        return redirect(url_for('intake.quiz'))
    path = catalog.get_path_by_key(interest)
    if path is None:
        abort(400)
    return redirect(url_for('paths.assess', path_id=path['id'], source='explicit'))


@intake_bp.get('/recommend/quiz')
def quiz():
    return render_template('quiz.html', questions=QUIZ, missing=request.args.get('missing') == '1')


@intake_bp.post('/recommend/quiz')
def quiz_submit():
    answers = {question['id']: request.form.get(question['id'], '') for question in QUIZ}
    active_keys = [path['path_key'] for path in catalog.list_active_paths()]
    result = score_quiz(answers, active_keys)

    if result['type'] == 'incomplete':
        return redirect(url_for('intake.quiz', missing=1))
    if result['type'] == 'winner':
        path = catalog.get_path_by_key(result['path_key'])
        return redirect(url_for('paths.assess', path_id=path['id'], source='quiz'))
    return redirect(url_for('intake.tie', candidates=','.join(result['candidates'])))


@intake_bp.get('/recommend/tie')
def tie():
    keys = [key for key in request.args.get('candidates', '').split(',') if key]
    paths = catalog.get_paths_by_keys(keys)
    if not paths:
        return redirect(url_for('intake.home'))
    return render_template('recommendation_tie.html', paths=paths)
