export default function HeroWordCloud() {
  return (
    <section className="hero-cloud" aria-label="Word cloud overview">
      <div className="page-shell">
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
