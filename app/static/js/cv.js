(() => {
  const state = window.PathForgeProgress.load();

  document.querySelectorAll('.cv-card').forEach((card) => {
    const slug = card.dataset.project;
    const unlocked = state[`project_${slug}_built`] === true && state[`project_${slug}_published`] === true;
    card.querySelectorAll('[data-when]').forEach((element) => {
      element.hidden = (element.dataset.when === 'unlocked') !== unlocked;
    });
  });
})();
