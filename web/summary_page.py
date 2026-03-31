"""Generate web/index.html + web/data.js from SQLite."""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
import sys
from pathlib import Path

# Repo root must be on sys.path when running `python web/summary_page.py` (not only `python -m web.summary_page`).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import db

HERE = Path(__file__).resolve().parent


def _load_json_col(raw: str | None) -> list:
    if not raw:
        return []
    try:
        x = json.loads(raw)
        return x if isinstance(x, list) else []
    except json.JSONDecodeError:
        return []


def export_data_js(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT t.id AS transcript_id, v.url, v.title, v.summary_text, v.core_lesson,
               v.key_concepts, v.difficulty, v.primary_topics, v.prerequisites,
               v.builds_toward, v.cluster_id, v.cluster_name, v.wordcloud_path,
               v.topic_buckets, v.is_persuasion_focused,
               v.duration_seconds, v.publish_date, v.downloaded_at
        FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        ORDER BY t.id
        """
    )
    lessons = []
    for row in cur.fetchall():
        lessons.append(
            {
                "transcript_id": int(row["transcript_id"]),
                "url": row["url"],
                "title": row["title"] or "",
                "summary_text": row["summary_text"] or "",
                "core_lesson": row["core_lesson"] or "",
                "key_concepts": _load_json_col(row["key_concepts"]),
                "difficulty": row["difficulty"] or "",
                "primary_topics": _load_json_col(row["primary_topics"]),
                "prerequisites": _load_json_col(row["prerequisites"]),
                "builds_toward": _load_json_col(row["builds_toward"]),
                "cluster_id": row["cluster_id"],
                "cluster_name": row["cluster_name"] or "",
                "wordcloud_path": row["wordcloud_path"] or "",
                "topic_buckets": _load_json_col(row["topic_buckets"]),
                "is_persuasion_focused": bool(row["is_persuasion_focused"])
                if row["is_persuasion_focused"] is not None
                else None,
                "duration_seconds": row["duration_seconds"],
                "publish_date": row["publish_date"] or "",
                "downloaded_at": row["downloaded_at"] or "",
            }
        )
    conn.close()

    stats = {
        "total_videos": len(lessons),
        "total_clusters": len({x["cluster_id"] for x in lessons if x["cluster_id"] is not None}),
        "topics": len(
            {b for x in lessons for b in (x["topic_buckets"] or [])}
        ),
        "persuasion_pct": round(
            100
            * sum(1 for x in lessons if x["is_persuasion_focused"] is True)
            / max(1, len(lessons)),
            1,
        ),
    }

    tree_path = Path("data/topic_tree.json")
    topic_tree = []
    if tree_path.is_file():
        topic_tree = json.loads(tree_path.read_text(encoding="utf-8"))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "lessons": lessons,
        "topic_tree": topic_tree,
    }
    return payload


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Scott Adams Persuasion Library</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #111; color: #e6e6e6; }
    header { padding: 1rem 2rem; background: #1a1a1a; border-bottom: 1px solid #333; }
    h1 { margin: 0 0 0.5rem 0; }
    .hero { width: 100%; max-height: 320px; object-fit: cover; }
    .bar { display: flex; gap: 2rem; padding: 0.75rem 2rem; background: #222; flex-wrap: wrap; }
    .wrap { padding: 1rem 2rem; max-width: 1400px; margin: 0 auto; }
    input[type=search] { width: min(480px, 100%); padding: 0.5rem; font-size: 1rem; }
    .tree { background: #1a1a1a; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    details { margin: 0.25rem 0; }
    .tree .vid-ref { font-size: 0.85rem; margin: 0.2rem 0; color: #ccc; }
    .tree .vid-ref span.id-tag { color: #8ab4f8; margin-right: 0.35rem; }
    .tree .vid-ref a { color: #8ab4f8; text-decoration: none; }
    .tree .vid-ref a:hover { text-decoration: underline; }
    .cluster-id { color: #888; font-size: 0.85rem; margin: 0.25rem 0; }
    .cluster-videos { margin: 0.5rem 0 0 0; padding-left: 1.1rem; font-size: 0.8rem; color: #bbb; max-height: 180px; overflow-y: auto; }
    .cluster-videos li { margin: 0.15rem 0; }
    .cluster-videos a { color: #8ab4f8; text-decoration: none; }
    .cluster-videos a:hover { text-decoration: underline; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
    .card { background: #1e1e1e; border-radius: 8px; padding: 0.75rem; border: 1px solid #333; }
    .badge-b { background: #1b5e20; color: #fff; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem; }
    .badge-i { background: #f9a825; color: #111; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem; }
    .badge-a { background: #b71c1c; color: #fff; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem; }
    .thumb { width: 200px; height: 100px; object-fit: cover; cursor: pointer; border-radius: 4px; }
    .card h3 a { color: #8ab4f8; text-decoration: none; }
    .card h3 a:hover { text-decoration: underline; }
    .watch-link { margin: 0.35rem 0 0 0; font-size: 0.9rem; }
    .watch-link a { color: #81c995; }
    .pill { display: inline-block; background: #333; padding: 0.1rem 0.35rem; margin: 0.1rem; border-radius: 4px; font-size: 0.8rem; }
    footer { padding: 1rem 2rem; color: #888; font-size: 0.9rem; }
    #modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 100; align-items: center; justify-content: center; }
    #modal.show { display: flex; }
    #modal img { max-width: 90vw; max-height: 90vh; }
  </style>
</head>
<body>
  <header>
    <h1>Scott Adams Persuasion Library</h1>
    <p>Local RAG pipeline export — open this file in a browser (no server).</p>
  </header>
  <img id="hero" class="hero" alt="Master word cloud" src="../wordclouds/master_wordcloud.png" onerror="this.style.display='none'"/>
  <div class="bar" id="statsBar"></div>
  <div class="wrap">
    <p><label>Search <input type="search" id="q" placeholder="Title, core lesson, key concepts…"/></label></p>
    <h2>Topic tree</h2>
    <p class="hint" style="color:#888;font-size:0.9rem;margin-top:0">Numbers like <code>#25</code> are <code>transcripts.id</code> in your database—matched to titles below.</p>
    <div class="tree" id="topicTree"></div>
    <h2>Clusters</h2>
    <p class="hint" style="color:#888;font-size:0.9rem;margin-top:0">Each card is a numeric <code>cluster_id</code> from KMeans. The LLM-chosen title can repeat for different ids—use <strong>Cluster #</strong> to tell them apart. Videos in the cluster are listed on each card.</p>
    <div class="grid" id="clusterGrid"></div>
    <h2>Videos</h2>
    <div class="grid" id="videoGrid"></div>
  </div>
  <footer id="foot"></footer>
  <div id="modal" onclick="this.classList.remove('show')"><img id="modalImg" alt="" src=""/></div>
  <script src="data.js"></script>
  <script>
  const DATA = window.SA_LESSONS_DATA;
  function badgeClass(d) {
    if (d === 'beginner') return 'badge-b';
    if (d === 'advanced') return 'badge-a';
    return 'badge-i';
  }
  function norm(s) { return (s || '').toLowerCase(); }
  function lessonMatches(q, L) {
    if (!q) return true;
    const hay = [L.title, L.core_lesson, L.summary_text, ...(L.key_concepts || [])].map(norm).join(' ');
    return q.split(/\\s+/).every(t => !t || hay.includes(t));
  }
  function render() {
    const q = (document.getElementById('q').value || '').trim().toLowerCase();
    const S = DATA.stats || {};
    document.getElementById('statsBar').innerHTML =
      `Videos: ${S.total_videos||0} &nbsp; Clusters: ${S.total_clusters||0} &nbsp; Topic tags: ${S.topics||0} &nbsp; Persuasion-focused: ${S.persuasion_pct||0}%`;
    document.getElementById('foot').textContent = 'Generated: ' + (DATA.generated_at||'') + ' — static export';

    const idToLesson = {};
    (DATA.lessons||[]).forEach(L => { idToLesson[L.transcript_id] = L; });

    const tree = DATA.topic_tree || [];
    const treeEl = document.getElementById('topicTree');
    treeEl.innerHTML = '';
    function walk(nodes) {
      const ul = document.createElement('ul');
      nodes.forEach(n => {
        const li = document.createElement('li');
        const det = document.createElement('details');
        const summ = document.createElement('summary');
        const lev = Number(n.level);
        const topic = (n.topic || '').trim();
        summ.textContent = (lev >= 1 && lev <= 3)
          ? ('Level ' + lev + ' — ' + topic)
          : topic;
        det.appendChild(summ);
        if ((n.subtopics||[]).length) {
          const s = document.createElement('div');
          s.textContent = 'Subtopics: ' + n.subtopics.join(', ');
          det.appendChild(s);
        }
        if ((n.recommended_video_ids||[]).length) {
          const wrap = document.createElement('div');
          wrap.textContent = 'Suggested order (database id → title):';
          det.appendChild(wrap);
          (n.recommended_video_ids||[]).forEach(vid => {
            const row = document.createElement('div');
            row.className = 'vid-ref';
            const L = idToLesson[vid];
            const sid = document.createElement('span');
            sid.className = 'id-tag';
            sid.textContent = '#' + vid;
            row.appendChild(sid);
            if (L && L.url) {
              const a = document.createElement('a');
              a.href = L.url;
              a.target = '_blank';
              a.rel = 'noopener noreferrer';
              a.textContent = L.title || L.url;
              row.appendChild(a);
            } else {
              row.appendChild(document.createTextNode(L ? (L.title || '') : '(not in this export)'));
            }
            det.appendChild(row);
          });
        }
        if (n.progression_note) {
          const pn = document.createElement('div');
          pn.style.marginTop = '0.35rem';
          pn.style.fontSize = '0.9rem';
          pn.style.color = '#aaa';
          pn.textContent = n.progression_note;
          det.appendChild(pn);
        }
        li.appendChild(det);
        ul.appendChild(li);
      });
      return ul;
    }
    if (tree.length) treeEl.appendChild(walk(tree));

    const byCluster = {};
    (DATA.lessons||[]).forEach(L => {
      const c = L.cluster_id;
      if (c == null) return;
      if (!byCluster[c]) byCluster[c] = [];
      byCluster[c].push(L);
    });
    const cg = document.getElementById('clusterGrid');
    cg.innerHTML = '';
    Object.keys(byCluster).sort((a,b)=>+a-+b).forEach(cid => {
      const list = byCluster[cid];
      list.sort((a,b) => (a.title||'').localeCompare(b.title||''));
      const name = (list[0] && list[0].cluster_name) || ('Cluster '+cid);
      const card = document.createElement('div');
      card.className = 'card';
      const img = document.createElement('img');
      img.src = '../wordclouds/clusters/cluster_' + cid + '.png';
      img.style.width = '100%'; img.style.maxHeight = '150px'; img.style.objectFit = 'cover';
      img.alt = 'Word cloud for cluster ' + cid;
      img.onerror = () => { img.style.display = 'none'; };
      card.appendChild(img);
      const h3 = document.createElement('h3');
      h3.textContent = name;
      card.appendChild(h3);
      const sub = document.createElement('p');
      sub.className = 'cluster-id';
      sub.textContent = 'Cluster #' + cid;
      card.appendChild(sub);
      const ct = document.createElement('p');
      ct.textContent = list.length + ' video' + (list.length === 1 ? '' : 's');
      card.appendChild(ct);
      const ul = document.createElement('ul');
      ul.className = 'cluster-videos';
      list.forEach(L => {
        const li = document.createElement('li');
        if (L.url) {
          const a = document.createElement('a');
          a.href = L.url;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          a.textContent = '#' + L.transcript_id + ' — ' + (L.title || '(no title)');
          li.appendChild(a);
        } else {
          li.textContent = '#' + L.transcript_id + ' — ' + (L.title || '(no title)');
        }
        ul.appendChild(li);
      });
      card.appendChild(ul);
      cg.appendChild(card);
    });

    const vg = document.getElementById('videoGrid');
    vg.innerHTML = '';
    (DATA.lessons||[]).filter(L => lessonMatches(q, L)).forEach(L => {
      const card = document.createElement('div');
      card.className = 'card';
      const h3 = document.createElement('h3');
      if (L.url) {
        const ta = document.createElement('a');
        ta.href = L.url;
        ta.target = '_blank';
        ta.rel = 'noopener noreferrer';
        ta.title = 'Open video on Locals';
        ta.textContent = L.title || 'Open on Locals';
        h3.appendChild(ta);
      } else {
        h3.textContent = L.title || '(no title)';
      }
      const sp = document.createElement('span');
      sp.className = badgeClass(L.difficulty || 'intermediate');
      sp.textContent = L.difficulty || 'intermediate';
      h3.appendChild(document.createTextNode(' '));
      h3.appendChild(sp);
      card.appendChild(h3);
      const desc = document.createElement('p');
      desc.textContent = L.core_lesson || L.summary_text || '';
      card.appendChild(desc);
      if (L.url) {
        const wl = document.createElement('p');
        wl.className = 'watch-link';
        const wa = document.createElement('a');
        wa.href = L.url;
        wa.target = '_blank';
        wa.rel = 'noopener noreferrer';
        wa.textContent = 'Open on Locals';
        wl.appendChild(wa);
        card.appendChild(wl);
      }
      if (L.wordcloud_path) {
        const th = document.createElement('img');
        th.className = 'thumb';
        th.src = '../' + L.wordcloud_path.replace(/^\\.\\//,'');
        th.alt = 'Word cloud';
        th.addEventListener('click', () => {
          const m = document.getElementById('modal');
          document.getElementById('modalImg').src = th.src.replace(/\\\\/g,'/');
          m.classList.add('show');
        });
        card.appendChild(th);
      }
      (L.primary_topics||[]).forEach(t => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.textContent = t;
        card.appendChild(pill);
      });
      vg.appendChild(card);
    });
  }
  document.getElementById('q').addEventListener('input', render);
  render();
  </script>
</body>
</html>
"""


def write_summary_page(db_path: str = "playlist_archive.db") -> None:
    t0 = time.perf_counter()
    payload = export_data_js(db_path)
    HERE.mkdir(parents=True, exist_ok=True)
    topic_browser_public = HERE.parent / "topic-browser" / "public"
    topic_browser_public.mkdir(parents=True, exist_ok=True)
    (topic_browser_public / "lessons.json").write_text(
        json.dumps(payload["lessons"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    js = "window.SA_LESSONS_DATA = " + json.dumps(payload, ensure_ascii=False) + ";"
    (HERE / "data.js").write_text(js, encoding="utf-8")
    (HERE / "index.html").write_text(HTML_TEMPLATE, encoding="utf-8")
    dt = time.perf_counter() - t0
    (HERE / "build_meta.json").write_text(
        json.dumps(
            {"seconds": round(dt, 3), "at": payload["generated_at"]},
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="playlist_archive.db")
    args = p.parse_args()
    db.init_db(args.db)
    write_summary_page(args.db)


if __name__ == "__main__":
    main()
