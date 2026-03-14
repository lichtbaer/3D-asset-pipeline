import { NavLink, Outlet } from "react-router-dom";
import { SubagentTaskPanel } from "./aria/SubagentTaskPanel.js";

export function Layout() {
  return (
    <div className="layout">
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
      <div className="layout-main">
        <main className="layout-content">
          <Outlet />
        </main>
        <SubagentTaskPanel />
      </div>
    </div>
  );
}
