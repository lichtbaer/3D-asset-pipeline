import { NavLink, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <>
      <nav className="main-nav" role="navigation">
        <NavLink
          to="/pipeline"
          className={({ isActive }) =>
            `main-nav__link ${isActive ? "main-nav__link--active" : ""}`
          }
        >
          Pipeline
        </NavLink>
        <NavLink
          to="/assets"
          className={({ isActive }) =>
            `main-nav__link ${isActive ? "main-nav__link--active" : ""}`
          }
        >
          Bibliothek
        </NavLink>
      </nav>
      <Outlet />
    </>
  );
}
