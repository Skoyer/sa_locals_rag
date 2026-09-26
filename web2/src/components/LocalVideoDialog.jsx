import { useEffect, useRef } from 'react';

/** Modal HTML5 player for locally served media (/media/video/{id}). */
export default function LocalVideoDialog({ open, title, streamUrl, onClose }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      className="local-video-dialog"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className="local-video-dialog__panel" onClick={(e) => e.stopPropagation()}>
        <header className="local-video-dialog__header">
          <div>
            <p className="local-video-dialog__eyebrow">Local file</p>
            <h2 className="local-video-dialog__title">{title}</h2>
          </div>
          <button type="button" className="local-video-dialog__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <video className="local-video-dialog__video" controls autoPlay preload="metadata" src={streamUrl} />
        <p className="local-video-dialog__hint">
          Streamed from your download folder — not locals.com.
        </p>
      </div>
    </dialog>
  );
}
