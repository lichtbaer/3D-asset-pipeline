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
        <NavLink
          to="/storage"
          className={({ isActive }) =>
            `main-nav__link ${isActive ? "main-nav__link--active" : ""}`
          }
        >
          Speicher
        </NavLink>
        <NavLink
          to="/presets"
          className={({ isActive }) =>
            `main-nav__link ${isActive ? "main-nav__link--active" : ""}`
          }
        >
          Presets
        </NavLink>
      </nav>
      <Outlet />
    </>
  );
}
