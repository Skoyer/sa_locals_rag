export default function PageHeader() {
  return (
    <header className="page-header">
      <div className="page-shell page-shell--header">
        <div className="page-header__row">
          <div className="page-header__text">
            <h1 className="page-header__title">Scott Adams Locals Micro Lessons Library</h1>
            <p className="page-header__subtitle">
              Browse Micro Lessons by theme, search the library, and open videos on Locals.
            </p>
          </div>
          <a
            className="page-header__logo-link"
            href="https://locals.com/scottadams/feed?playlist=102"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open Scott Adams on Locals (playlist)"
          >
            <div className="page-header__logo-frame">
              <img
                className="page-header__logo"
                src="/logo.png"
                alt=""
                decoding="async"
              />
            </div>
          </a>
        </div>
      </div>
    </header>
  );
}
