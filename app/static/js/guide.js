// Start guide checklist: saved in the same per-path progress store as the Progress page.
(() => {
  const state = window.PathForgeProgress.load();
  const inputs = [...document.querySelectorAll('#guide input[type="checkbox"]')];
  const count = document.getElementById('guide-count');
  const bar = document.getElementById('guide-bar');

  function render() {
    const done = inputs.filter((input) => input.checked).length;
    count.textContent = `${done} of ${inputs.length} done`;
    bar.style.width = inputs.length ? `${Math.round((done / inputs.length) * 100)}%` : '0%';
    inputs.forEach((input) => input.closest('.timeline-step').classList.toggle('is-done', input.checked));
  }

  inputs.forEach((input) => {
    input.checked = state[input.dataset.key] === true;
    input.addEventListener('change', () => {
      state[input.dataset.key] = input.checked;
      window.PathForgeProgress.save(state);
      render();
    });
  });
  render();
})();
