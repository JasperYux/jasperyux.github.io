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
  const input = document.querySelector("#search");
  if (!input) return;
  const cards = [...document.querySelectorAll(".post-card")];
  const empty = document.querySelector("#empty");
  const count = document.querySelector("#result-count");
  const clear = document.querySelector("#clear-filter");
  let year = "";
  function filter() {
    const query = input.value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const card of cards) {
      card.hidden = !(
        (!year || card.dataset.year === year) &&
        card.dataset.search.includes(query)
      );
      if (!card.hidden) visible++;
    }
    empty.hidden = visible !== 0;
    count.textContent = `${visible} 篇记录${year ? ` · ${year}` : ""}`;
    clear.hidden = !year && !query;
  }
  input.addEventListener("input", filter);
  document.querySelectorAll("[data-filter-year]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      year = link.dataset.filterYear;
      filter();
      document.querySelector("#articles").scrollIntoView({ behavior: "auto" });
    });
  });
  clear.addEventListener("click", () => {
    year = "";
    input.value = "";
    filter();
  });
})();
