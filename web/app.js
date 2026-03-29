(function () {
  const DATA = window.SA_LESSONS_DATA;

  let filterQuery = '';
  let debounceTimer = null;
  let activeThemeId = null;

  function normalizeClusterTitle(raw) {
    if (!raw) return '';
    return raw
      .replace(/^Micro Lessons? on\s+/i, '')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
  }

  function normalizeVideoTitle(raw, transcriptId) {
    if (!raw && transcriptId == null) return '';
    const rawStr = raw || '';
    const episodeMatch = rawStr.match(/^#(\d+)\s*[—:-]?\s*/);
    const episodeNumber = episodeMatch
      ? episodeMatch[1]
      : transcriptId != null
        ? String(transcriptId)
        : null;
    let title = rawStr.replace(/^#\d+\s*[—:-]?\s*/i, '');
    title = title.replace(/^A Micro Lesson (on|about)\s+/i, '');
    title = title.trim();
    if (!title) title = transcriptId != null ? 'Lesson' : '';
    title = title.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
    if (episodeNumber) {
      return `${title} (#${episodeNumber})`;
    }
    return title;
  }

  function clusterDisplayTitle(cluster) {
    if (cluster && cluster.title2) return cluster.title2;
    return normalizeClusterTitle(cluster.title_original || cluster.cluster_name || '');
  }

  function videoDisplayTitle(L) {
    if (L.display_title) return L.display_title;
    const raw = L.title_original != null ? L.title_original : L.title;
    return normalizeVideoTitle(raw, L.transcript_id);
  }

  function videoTooltipText(L) {
    const d = L.short_description || L.summary_text || L.core_lesson || '';
    return d ? String(d).trim() : 'Micro lesson video';
  }

  function norm(s) {
    return (s || '').toLowerCase();
  }

  function lessonSearchMatches(q, L) {
    if (!q) return true;
    const display = videoDisplayTitle(L);
    const hay = [
      display,
      L.short_description,
      L.summary_text,
      L.core_lesson,
      L.title,
      ...(L.key_concepts || []),
    ]
      .filter(Boolean)
      .map(norm)
      .join(' ');
    return q.split(/\s+/).every((t) => !t || hay.includes(t));
  }

  function lessonMatchesFilters(L, q, themeId) {
    if (themeId != null && themeId !== '' && String(L.cluster_id) !== String(themeId)) {
      return false;
    }
    return lessonSearchMatches(q, L);
  }

  function getSearchInputEl() {
    return document.getElementById('lesson-search');
  }

  function updateClearButton() {
    const input = getSearchInputEl();
    const clearBtn = document.getElementById('search-clear');
    if (!input || !clearBtn) return;
    clearBtn.hidden = !input.value;
  }

  function scheduleFilterFromInput(immediate) {
    const input = getSearchInputEl();
    if (!input) return;
    const raw = (input.value || '').trim().toLowerCase();
    if (immediate) {
      filterQuery = raw;
      clearTimeout(debounceTimer);
      render();
      return;
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      filterQuery = raw;
      render();
    }, 250);
  }

  function renderFilterBar() {
    const bar = document.getElementById('filter-bar');
    if (!bar) return;
    const input = getSearchInputEl();
    const qRaw = input ? input.value.trim() : '';
    const hasTheme = activeThemeId != null;
    const hasSearch = qRaw.length > 0;
    if (!hasTheme && !hasSearch) {
      bar.hidden = true;
      bar.innerHTML = '';
      return;
    }
    bar.hidden = false;
    const clusters = buildClusters(DATA.lessons || []);
    let themeName = '';
    if (hasTheme) {
      const row = clusters.find((c) => String(c.cid) === String(activeThemeId));
      if (row && row.list[0]) {
        const f = row.list[0];
        themeName = clusterDisplayTitle({
          title2: f.title2,
          title_original: f.cluster_name,
          cluster_name: f.cluster_name,
        });
      }
    }
    let html = '';
    if (hasTheme) {
      html += `<span class="filter-chip">Theme: <strong>${escapeHtml(themeName || 'Cluster #' + activeThemeId)}</strong></span>`;
    }
    if (hasTheme && hasSearch) {
      html += '<span class="filter-bar__sep" aria-hidden="true"> · </span>';
    }
    if (hasSearch) {
      html += `<span class="filter-chip filter-chip--muted">Search: &ldquo;${escapeHtml(qRaw)}&rdquo;</span>`;
    }
    html += `<button type="button" class="btn-reset" id="reset-filters">Reset filters</button>`;
    bar.innerHTML = html;
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        activeThemeId = null;
        if (input) input.value = '';
        filterQuery = '';
        clearTimeout(debounceTimer);
        updateClearButton();
        render();
      });
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildClusters(lessons) {
    const byCluster = {};
    (lessons || []).forEach((L) => {
      const c = L.cluster_id;
      if (c == null) return;
      if (!byCluster[c]) byCluster[c] = [];
      byCluster[c].push(L);
    });
    return Object.keys(byCluster)
      .sort((a, b) => +a - +b)
      .map((cid) => ({
        cid,
        list: byCluster[cid].sort((a, b) => (a.title || '').localeCompare(b.title || '')),
      }));
  }

  function render() {
    const S = DATA.stats || {};
    const statsLine = document.getElementById('stats-line');
    if (statsLine) {
      statsLine.innerHTML = `Videos: ${S.total_videos || 0} &nbsp; Clusters: ${S.total_clusters || 0} &nbsp; Topic tags: ${S.topics || 0}`;
    }
    const foot = document.getElementById('foot');
    if (foot) {
      foot.textContent = 'Generated: ' + (DATA.generated_at || '') + ' — static export';
    }

    renderFilterBar();

    const lessons = (DATA.lessons || []).filter((L) => lessonMatchesFilters(L, filterQuery, activeThemeId));

    const emptyEl = document.getElementById('lesson-list-empty');
    const listEl = document.getElementById('lesson-list');
    if (emptyEl && listEl) {
      if (lessons.length === 0) {
        emptyEl.hidden = false;
        emptyEl.textContent = 'No lessons match your filters.';
        listEl.innerHTML = '';
      } else {
        emptyEl.hidden = true;
        listEl.innerHTML = '';
        lessons.forEach((L) => {
          const li = document.createElement('li');
          li.className = 'lesson-list__item';
          li.setAttribute('role', 'listitem');
          const title = videoDisplayTitle(L);
          const tip = videoTooltipText(L);
          const excerpt = (L.short_description || L.summary_text || L.core_lesson || '').trim();
          const themeTag = (L.primary_topics && L.primary_topics[0]) || L.cluster_name || '';
          const meta = '#' + L.transcript_id + (themeTag ? ' · ' + themeTag : '');

          if (L.url) {
            const a = document.createElement('a');
            a.href = L.url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.className = 'lesson-row';
            a.title = tip;
            a.innerHTML =
              '<span class="lesson-row__title">' +
              escapeHtml(title) +
              '</span>' +
              (excerpt
                ? '<span class="lesson-row__excerpt">' + escapeHtml(excerpt.length > 160 ? excerpt.slice(0, 157) + '…' : excerpt) + '</span>'
                : '') +
              '<span class="lesson-row__meta">' +
              escapeHtml(meta) +
              '</span>';
            li.appendChild(a);
          } else {
            const div = document.createElement('div');
            div.className = 'lesson-row lesson-row--static';
            div.innerHTML =
              '<span class="lesson-row__title">' +
              escapeHtml(title) +
              '</span>' +
              (excerpt
                ? '<span class="lesson-row__excerpt">' + escapeHtml(excerpt.length > 160 ? excerpt.slice(0, 157) + '…' : excerpt) + '</span>'
                : '') +
              '<span class="lesson-row__meta">' +
              escapeHtml(meta) +
              '</span>';
            li.appendChild(div);
          }
          listEl.appendChild(li);
        });
      }
    }

    const clusters = buildClusters(DATA.lessons || []);
    const tg = document.getElementById('theme-grid');
    if (tg) {
      tg.innerHTML = '';
      clusters.forEach(({ cid, list }) => {
        const first = list[0] || {};
        const name = clusterDisplayTitle({
          title2: first.title2,
          title_original: first.cluster_name,
          cluster_name: first.cluster_name,
        });
        const label = name || 'Cluster ' + cid;
        const isActive = String(activeThemeId) === String(cid);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'theme-card' + (isActive ? ' theme-card--active' : '');
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        btn.setAttribute('aria-label', `Filter library by theme: ${label}. ${list.length} lessons.`);
        const img = document.createElement('img');
        img.className = 'theme-card__thumb';
        img.src = '../wordclouds/clusters/cluster_' + cid + '.png';
        img.alt = '';
        img.onerror = () => {
          img.style.display = 'none';
        };
        const titleSpan = document.createElement('span');
        titleSpan.className = 'theme-card__title';
        titleSpan.textContent = label;
        const metaSpan = document.createElement('span');
        metaSpan.className = 'theme-card__meta';
        metaSpan.textContent = `Cluster #${cid} · ${list.length} lesson${list.length === 1 ? '' : 's'}`;
        btn.appendChild(img);
        btn.appendChild(titleSpan);
        btn.appendChild(metaSpan);
        btn.addEventListener('click', () => {
          activeThemeId = String(activeThemeId) === String(cid) ? null : cid;
          render();
        });
        tg.appendChild(btn);
      });
    }
  }

  function init() {
    const search = getSearchInputEl();
    const clearBtn = document.getElementById('search-clear');

    if (search) {
      search.addEventListener('input', () => {
        updateClearButton();
        renderFilterBar();
        scheduleFilterFromInput(false);
      });
      search.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          scheduleFilterFromInput(true);
        }
        if (e.key === 'Escape') {
          e.preventDefault();
          search.value = '';
          filterQuery = '';
          clearTimeout(debounceTimer);
          updateClearButton();
          render();
        }
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (search) search.value = '';
        filterQuery = '';
        clearTimeout(debounceTimer);
        updateClearButton();
        render();
      });
    }
    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
