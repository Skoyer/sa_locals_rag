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
          <div className="page-header__logo-frame">
            <img
              className="page-header__logo"
              src="/logo.png"
              alt="Scott Adams Locals Micro Lessons Library logo"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
