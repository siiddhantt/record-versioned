const state = {
  data: null,
  storyType: "all",
  storyQuery: "",
  scope: "all",
  evidenceQuery: "",
};

const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const normalize = (value) => String(value).toLowerCase().replace(/\s+/g, " ").trim();
const unique = (values) => [...new Set(values)];

const alignmentSearchText = (item) =>
  normalize(
    [
      item.scope_label,
      item.classification,
      item.left.heading,
      item.left.context,
      item.right.heading,
      item.right.context,
      item.review_note,
    ].join(" "),
  );

const storySearchText = (story) =>
  normalize(
    [
      story.type,
      story.kicker,
      story.title,
      story.summary,
      story.why_it_matters,
      ...story.alignment_indices.map((index) => alignmentSearchText(state.data.alignments[index])),
    ].join(" "),
  );

const sourceLink = (side, label = "Open scanned page") => `
  <a class="source-link" href="${escapeHtml(side.source_url)}" target="_blank" rel="noreferrer">
    ${escapeHtml(label)} <span aria-hidden="true">↗</span>
  </a>
`;

const renderTimeline = () => {
  document.querySelector("#timeline-list").innerHTML = state.data.volumes
    .map(
      (volume, index) => `
        <li>
          <div class="timeline-index" aria-hidden="true">0${index + 1}</div>
          <span class="volume-label">${escapeHtml(volume.label)}</span>
          <span class="volume-meta">Catalogue date ${escapeHtml(volume.catalogue_date)}</span>
          <p>${volume.page_count} scanned pages</p>
          <a href="${escapeHtml(volume.source_url)}" target="_blank" rel="noreferrer">
            View original report <span aria-hidden="true">↗</span>
          </a>
        </li>
      `,
    )
    .join("");
};

const renderStoryFilters = () => {
  const types = ["all", ...unique(state.data.stories.map((story) => story.type))];
  document.querySelector("#story-filters").innerHTML = types
    .map(
      (type) => `
        <button
          class="filter-chip"
          type="button"
          data-story-type="${escapeHtml(type)}"
          aria-pressed="${String(state.storyType === type)}"
        >${type === "all" ? "All changes" : escapeHtml(type)}</button>
      `,
    )
    .join("");

  document.querySelectorAll("[data-story-type]").forEach((button) => {
    button.addEventListener("click", () => {
      state.storyType = button.dataset.storyType;
      renderStoryFilters();
      renderStories();
    });
  });
};

const renderStories = () => {
  const query = normalize(state.storyQuery);
  const stories = state.data.stories.filter(
    (story) =>
      (state.storyType === "all" || story.type === state.storyType) &&
      (!query || storySearchText(story).includes(query)),
  );

  document.querySelector("#story-result-count").textContent =
    `${stories.length} reviewed thread${stories.length === 1 ? "" : "s"}`;
  document.querySelector("#story-empty").hidden = stories.length !== 0;
  document.querySelector("#story-grid").innerHTML = stories
    .map(
      (story, index) => `
        <article class="story-card ${index === 0 ? "story-card-featured" : ""}">
          <div class="story-topline">
            <span>${escapeHtml(story.kicker)}</span>
            <span>${escapeHtml(story.type)}</span>
          </div>
          <div>
            <h3>${escapeHtml(story.title)}</h3>
            <p>${escapeHtml(story.summary)}</p>
          </div>
          <button class="story-open" type="button" data-story-id="${escapeHtml(story.id)}">
            Follow the evidence <span aria-hidden="true">→</span>
          </button>
        </article>
      `,
    )
    .join("");

  document.querySelectorAll("[data-story-id]").forEach((button) => {
    button.addEventListener("click", () => openStory(button.dataset.storyId));
  });
};

const renderFilters = () => {
  const select = document.querySelector("#scope-filter");
  const scopes = [
    ...state.data.scopes,
    ...(state.data.alignments.some((item) => item.scope === "unscoped")
      ? [{ id: "unscoped", label: "Unscoped report section" }]
      : []),
  ];
  select.insertAdjacentHTML(
    "beforeend",
    scopes
      .map((scope) => `<option value="${escapeHtml(scope.id)}">${escapeHtml(scope.label)}</option>`)
      .join(""),
  );
};

const excerptMarkup = (side) => `
  <article class="excerpt">
    <span class="volume-meta">${escapeHtml(side.volume_label)} | scan page n${side.page_index}</span>
    <h4>${escapeHtml(side.heading)}</h4>
    <p>${escapeHtml(side.context)}</p>
    ${sourceLink(side, "Verify source")}
  </article>
`;

const groupLabel = (item) => `${item.left.volume_label} to ${item.right.volume_label}`;

const renderEvidence = () => {
  const query = normalize(state.evidenceQuery);
  const items = state.data.alignments
    .filter(
      (item) =>
        (state.scope === "all" || item.scope === state.scope) &&
        (!query || alignmentSearchText(item).includes(query)),
    )
    .sort(
      (left, right) =>
        left.left.year - right.left.year ||
        left.left.page_index - right.left.page_index ||
        left.scope_label.localeCompare(right.scope_label),
    );

  document.querySelector("#result-count").textContent =
    `${items.length} of ${state.data.alignments.length} validated alignment${items.length === 1 ? "" : "s"}`;

  const groups = items.reduce((result, item) => {
    const key = groupLabel(item);
    if (!result.has(key)) result.set(key, []);
    result.get(key).push(item);
    return result;
  }, new Map());

  document.querySelector("#evidence-list").innerHTML = groups.size
    ? [...groups.entries()]
        .map(
          ([label, groupItems], groupIndex) => `
            <details class="evidence-group" ${groupIndex === 0 && (state.scope !== "all" || query) ? "open" : ""}>
              <summary>
                <span>${escapeHtml(label)}</span>
                <span>${groupItems.length} alignment${groupItems.length === 1 ? "" : "s"}</span>
              </summary>
              <div class="evidence-list">
                ${groupItems
                  .map(
                    (item) => `
                      <article class="evidence-card">
                        <header class="card-header">
                          <div>
                            <p class="scope-label">${escapeHtml(item.scope_label)}</p>
                            <p>${escapeHtml(item.review_note)}</p>
                          </div>
                          <span class="badge">
                            ${item.classification === "same" ? "Same section" : "Reviewed rename"}
                          </span>
                        </header>
                        <div class="pair">
                          ${excerptMarkup(item.left)}
                          ${excerptMarkup(item.right)}
                        </div>
                      </article>
                    `,
                  )
                  .join("")}
              </div>
            </details>
          `,
        )
        .join("")
    : `<div class="empty-state"><p>No validated evidence matches those filters.</p></div>`;
};

const dialogEvidenceMarkup = (item) => `
  <section class="dialog-pair" aria-label="${escapeHtml(groupLabel(item))}">
    <div class="dialog-pair-heading">
      <p>${escapeHtml(item.scope_label)}</p>
      <span>${escapeHtml(groupLabel(item))}</span>
    </div>
    <div class="pair">
      ${excerptMarkup(item.left)}
      ${excerptMarkup(item.right)}
    </div>
  </section>
`;

const openStory = (storyId) => {
  const story = state.data.stories.find((item) => item.id === storyId);
  if (!story) return;

  document.querySelector("#dialog-kicker").textContent = `${story.kicker} | ${story.type}`;
  document.querySelector("#dialog-title").textContent = story.title;
  document.querySelector("#dialog-summary").textContent = story.summary;
  document.querySelector("#dialog-insight").innerHTML = `
    <span>Why it matters</span>
    <p>${escapeHtml(story.why_it_matters)}</p>
  `;
  document.querySelector("#dialog-evidence").innerHTML = story.alignment_indices
    .map((index) => dialogEvidenceMarkup(state.data.alignments[index]))
    .join("");

  const dialog = document.querySelector("#story-dialog");
  dialog.showModal();
  document.querySelector("#dialog-close").focus();
};

const closeStory = () => document.querySelector("#story-dialog").close();

const bindEvents = () => {
  document.querySelector("#story-search").addEventListener("input", (event) => {
    state.storyQuery = event.target.value;
    renderStories();
  });

  document.querySelector("#clear-story-search").addEventListener("click", () => {
    state.storyQuery = "";
    state.storyType = "all";
    document.querySelector("#story-search").value = "";
    renderStoryFilters();
    renderStories();
    document.querySelector("#story-search").focus();
  });

  document.querySelector("#scope-filter").addEventListener("change", (event) => {
    state.scope = event.target.value;
    renderEvidence();
  });

  document.querySelector("#evidence-search").addEventListener("input", (event) => {
    state.evidenceQuery = event.target.value;
    renderEvidence();
  });

  document.querySelector("#dialog-close").addEventListener("click", closeStory);
  document.querySelector("#story-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeStory();
  });
};

const render = () => {
  document.querySelector("#description").textContent =
    "Follow programs, funding, and public institutions across annual reports, with every conclusion tied to the original scanned pages.";
  document.querySelector("#valid-count").textContent = state.data.review.valid_count;
  document.querySelector("#hero-valid-count").textContent = state.data.review.valid_count;
  document.querySelector("#reviewed-count").textContent = state.data.review.reviewed_count;
  const precision = `${(state.data.review.precision * 100).toFixed(1)}%`;
  document.querySelector("#precision").textContent = precision;
  document.querySelector("#hero-precision").textContent = precision;
  document.querySelector("#limitations").innerHTML = state.data.limitations
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");

  renderStoryFilters();
  renderStories();
  renderTimeline();
  renderFilters();
  renderEvidence();
  bindEvents();
};

fetch(new URL("./data.json", import.meta.url))
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load evidence data: ${response.status}`);
    return response.json();
  })
  .then((data) => {
    state.data = data;
    render();
  })
  .catch((error) => {
    document.querySelector("#description").textContent = error.message;
  });
