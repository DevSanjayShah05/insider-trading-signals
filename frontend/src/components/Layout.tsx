import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

const NAV_LINKS = [
  { to: "/", label: "Leaderboard", end: true },
  { to: "/methodology", label: "Methodology", end: true },
];

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand" style={{ pointerEvents: "auto" }}>
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-text">
            <span className="brand-title">Paper Trail</span>
            <span className="brand-sub">Insider Cluster-Buy Signals</span>
          </span>
        </NavLink>
        <nav className="top-nav">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="top-spacer" />
        <div className="case-pill">
          <span>SEC FORM 4 · CODE P/A</span>
        </div>
      </header>
      <main style={{ flex: 1 }}>{children}</main>
      <footer className="footer">
        Paper Trail is a portfolio project. <strong>Not investment advice.</strong>{" "}
        Insider transaction data sourced from SEC DERA Form 3/4/5 bulk data sets; forward
        prices from Yahoo Finance via <code>yfinance</code>. Educational/portfolio use only.
      </footer>
    </div>
  );
}
