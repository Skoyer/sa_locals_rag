import { useEffect, useState } from 'react';

const SCROLL_HIDE_PX = 56;

export default function HeroWordCloud() {
  const [hiddenByScroll, setHiddenByScroll] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setHiddenByScroll(window.scrollY > SCROLL_HIDE_PX);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <section
      className={`hero-cloud${hiddenByScroll ? ' hero-cloud--hidden' : ''}`}
      aria-label="Word cloud overview"
      aria-hidden={hiddenByScroll}
    >
      <div className="page-shell hero-cloud__inner">
        <div className="hero-cloud__frame">
          <img
            className="hero-cloud__img"
            alt="Master word cloud"
            src="/wordclouds/master_wordcloud.png"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        </div>
      </div>
    </section>
  );
}
