import { useEffect, useRef } from 'react';

export default function WordcloudDialog({ payload, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (payload) {
      if (!el.open) el.showModal();
    } else if (el.open) {
      el.close();
    }
  }, [payload]);

  return (
    <dialog
      ref={ref}
      className="wc-dialog"
      aria-labelledby="wc-dialog-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="wc-dialog__panel" role="document">
        <button type="button" className="wc-dialog__close" onClick={onClose} aria-label="Close preview">
          ×
        </button>
        {payload?.src ? (
          <div className="wc-dialog__img-wrap">
            <img src={payload.src} alt="" className="wc-dialog__img" />
          </div>
        ) : null}
        <h2 id="wc-dialog-title" className="wc-dialog__title">
          {payload?.title ?? ''}
        </h2>
        {payload?.href ? (
          <a
            href={payload.href}
            target="_blank"
            rel="noopener noreferrer"
            className="wc-dialog__cta"
          >
            Watch on Locals
          </a>
        ) : (
          <p className="wc-dialog__cta wc-dialog__cta--muted">No link available</p>
        )}
      </div>
    </dialog>
  );
}
