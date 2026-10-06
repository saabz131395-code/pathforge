// Level check: show one question at a time with a progress bar.
// Without JavaScript every question is shown at once and the form still works.
(() => {
  const form = document.getElementById('assess-form');
  if (!form) return;

  const questions = [...form.querySelectorAll('.assess-question')];
  const back = document.getElementById('assess-back');
  const next = document.getElementById('assess-next');
  const submit = document.getElementById('assess-submit');
  const stepLabel = document.getElementById('assess-step');
  const tierLabel = document.getElementById('assess-tier');
  const bar = document.getElementById('assess-bar');
  let current = 0;
  let usingPointer = false; // keyboard users move with arrow keys, so never auto-advance for them
  form.addEventListener('pointerdown', () => { usingPointer = true; });
  form.addEventListener('keydown', () => { usingPointer = false; });

  form.classList.add('is-stepper');
  back.hidden = false;
  next.hidden = false;

  const answered = (fieldset) => fieldset.querySelector('input:checked') !== null;

  function show(index) {
    current = index;
    questions.forEach((fieldset, i) => { fieldset.hidden = i !== index; });
    const isLast = index === questions.length - 1;
    back.disabled = index === 0;
    next.hidden = isLast;
    submit.hidden = !isLast;
    next.disabled = !answered(questions[index]);
    submit.disabled = !answered(questions[index]);
    stepLabel.textContent = `Question ${index + 1} of ${questions.length}`;
    const tier = questions[index].dataset.tier;
    tierLabel.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);
    bar.style.width = `${Math.round((index / questions.length) * 100)}%`;
    const first = questions[index].querySelector('input:checked') || questions[index].querySelector('input');
    if (first) first.focus({ preventScroll: true });
  }

  form.addEventListener('change', (event) => {
    if (!event.target.matches('input[type="radio"]')) return;
    next.disabled = false;
    submit.disabled = false;
    // Move on automatically after a short pause, so answering feels quick.
    if (usingPointer && current < questions.length - 1) {
      window.setTimeout(() => { if (answered(questions[current])) show(current + 1); }, 350);
    }
  });

  next.addEventListener('click', () => { if (current < questions.length - 1) show(current + 1); });
  back.addEventListener('click', () => { if (current > 0) show(current - 1); });

  form.addEventListener('submit', () => {
    bar.style.width = '100%';
    submit.disabled = true;
    submit.textContent = 'Building your plan…';
  });

  show(0);
})();
