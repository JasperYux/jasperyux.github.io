(() => {
  // Preserve links from the previous hash-routed frontend.
  function redirectLegacy() {
    const legacy = location.hash.match(
      /^#\/(?:post|posts|issue|issues)\/(\d+)(?:\/|$)/,
    );
    if (legacy) location.replace(`/posts/${legacy[1]}/`);
    return Boolean(legacy);
  }
  window.addEventListener("hashchange", redirectLegacy);
  if (redirectLegacy()) return;
})();
