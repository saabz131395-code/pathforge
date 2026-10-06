// Shared helper: read/write one path's progress in localStorage.
// Progress is keyed by the permanent path key + project slug, so it survives re-seeding.
// Every storage call is wrapped, because private browsing or blocked cookies can make
// localStorage throw instead of just being empty.
window.PathForgeProgress = (() => {
  const storageKey = 'pathforge_progress_' + window.PATH_KEY;

  function load() {
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || '{}');
      return saved && typeof saved === 'object' ? saved : {};
    } catch (error) {
      return {};
    }
  }

  function save(state) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(state));
      return true;
    } catch (error) {
      return false;
    }
  }

  return { load, save };
})();
