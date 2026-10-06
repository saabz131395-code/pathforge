(() => {
  const state = window.PathForgeProgress.load();
  const inputs = [...document.querySelectorAll('#progress input[type="checkbox"]')];
  const count = document.getElementById('progress-count');
  const bar = document.getElementById('progress-bar');
  const warning = document.getElementById('storage-warning');

  function render() {
    const completed = inputs.filter((input) => input.checked).length;
    const total = inputs.length;
    count.textContent = `${completed} of ${total} complete`;
    bar.style.width = total ? `${Math.round((completed / total) * 100)}%` : '0%';
  }

  inputs.forEach((input) => {
    input.checked = state[input.dataset.key] === true;
    input.addEventListener('change', () => {
      state[input.dataset.key] = input.checked;
      if (!window.PathForgeProgress.save(state) && warning) warning.hidden = false;
      render();
    });
  });
  render();
})();
