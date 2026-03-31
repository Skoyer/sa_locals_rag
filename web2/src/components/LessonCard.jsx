import { useLayoutEffect, useRef, useState } from 'react';
import {
  buildLessonMetaSegments,
  lessonWordcloudSrc,
  videoDisplayTitle,
  videoTooltipText,
} from '../normalize.js';
import { useMediaQuery } from '../hooks/useMediaQuery.js';

function PlayChevron() {
  return (
    <svg className="lesson-card__play-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.14" />
      <path fill="currentColor" d="M9.5 7.5v9L17 12 9.5 7.5z" />
    </svg>
  );
}

const PREVIEW_W = 280;

export default function LessonCard({ L, onOpenWordcloudModal }) {
  const title = videoDisplayTitle(L);
  const tip = videoTooltipText(L);
  const excerpt = (L.short_description || L.summary_text || L.core_lesson || '').trim();
  const metaLine = buildLessonMetaSegments(L).join(' · ');
  const href = L.url || '#';
  const wcSrc = lessonWordcloudSrc(L);

  const [imgFailed, setImgFailed] = useState(false);
  const [hoverOpen, setHoverOpen] = useState(false);
  const [previewPos, setPreviewPos] = useState(null);
  const thumbGroupRef = useRef(null);

  const prefersHover = useMediaQuery('(hover: hover)');
  const showHoverPreview = prefersHover && hoverOpen && wcSrc && !imgFailed;

  useLayoutEffect(() => {
    if (!showHoverPreview || !thumbGroupRef.current) {
      setPreviewPos(null);
      return;
    }
    const el = thumbGroupRef.current;
    const r = el.getBoundingClientRect();
    const pad = 12;
    let left = r.right - 10;
    if (left + PREVIEW_W > window.innerWidth - pad) {
      left = r.left - PREVIEW_W + 10;
    }
    left = Math.max(pad, Math.min(left, window.innerWidth - PREVIEW_W - pad));
    const maxH = Math.min(260, window.innerHeight - pad * 2);
    let top = r.top;
    if (top + maxH > window.innerHeight - pad) {
      top = Math.max(pad, window.innerHeight - pad - maxH);
    }
    setPreviewPos({ top, left, maxH });
  }, [showHoverPreview]);

  useLayoutEffect(() => {
    if (!showHoverPreview) return;
    const onScroll = () => setHoverOpen(false);
    window.addEventListener('scroll', onScroll, true);
    return () => window.removeEventListener('scroll', onScroll, true);
  }, [showHoverPreview]);

  const openModal = () => {
    if (!wcSrc || imgFailed) return;
    onOpenWordcloudModal({ title, src: wcSrc, href: L.url || null });
  };

  const mainInner = (
    <>
      <div className="lesson-card__body">
        <h3 className="lesson-card__title">{title}</h3>
        {excerpt ? <p className="lesson-card__excerpt">{excerpt}</p> : null}
        {metaLine ? <p className="lesson-card__meta">{metaLine}</p> : null}
      </div>
      <span className="lesson-card__play">
        <PlayChevron />
        <span className="lesson-card__play-label">Play</span>
      </span>
    </>
  );

  const thumbBlock =
    wcSrc && !imgFailed ? (
      <div
        ref={thumbGroupRef}
        className="lesson-card__thumb-group"
        onMouseEnter={() => setHoverOpen(true)}
        onMouseLeave={() => setHoverOpen(false)}
      >
        <div className="lesson-card__thumb-frame">
          <img
            className="lesson-card__thumb-img"
            src={wcSrc}
            alt=""
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        </div>
        <button
          type="button"
          className="lesson-card__thumb-hit"
          aria-label="Open word cloud preview"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            openModal();
          }}
        />
        {showHoverPreview && previewPos ? (
          <div
            className="lesson-card__wc-preview-pop"
            style={{
              top: previewPos.top,
              left: previewPos.left,
              width: PREVIEW_W,
              maxHeight: previewPos.maxH,
            }}
            aria-hidden="true"
          >
            <img src={wcSrc} alt="" />
          </div>
        ) : null}
      </div>
    ) : (
      <div className="lesson-card__thumb-frame lesson-card__thumb-frame--empty" aria-hidden="true" />
    );

  return (
    <div
      className={`lesson-card${L.url ? '' : ' lesson-card--static'} lesson-card--with-thumb`}
    >
      <div className="lesson-card__thumb-col">{thumbBlock}</div>
      {L.url ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="lesson-card__main"
          title={tip}
          aria-label={`Open video: ${title}`}
        >
          {mainInner}
        </a>
      ) : (
        <div className="lesson-card__main lesson-card__main--static" aria-label={`${title} (no link)`}>
          {mainInner}
        </div>
      )}
    </div>
  );
}
