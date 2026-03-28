import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProviderHealthBadge } from "../../components/providers/ProviderHealthBadge.js";

describe("ProviderHealthBadge", () => {
  it("rendert healthy-Status", () => {
    render(<ProviderHealthBadge status="healthy" />);
    const badge = screen.getByLabelText(/Provider-Status: Verfügbar/);
    expect(badge.className).toContain("provider-health-badge--healthy");
  });

  it("rendert unavailable-Status", () => {
    render(<ProviderHealthBadge status="unavailable" reason="API-Key fehlt" />);
    const badge = screen.getByLabelText(/Provider-Status: Nicht verfügbar/);
    expect(badge).toBeDefined();
  });

  it("rendert degraded-Status", () => {
    render(<ProviderHealthBadge status="degraded" reason="Eingeschränkt" />);
    const badge = screen.getByLabelText(/Provider-Status: Eingeschränkt/);
    expect(badge).toBeDefined();
  });

  it("zeigt Label nur bei size=lg", () => {
    const { rerender } = render(<ProviderHealthBadge status="healthy" size="sm" />);
    expect(screen.queryByText("Verfügbar")).toBeNull();

    rerender(<ProviderHealthBadge status="healthy" size="lg" />);
    expect(screen.getByText("Verfügbar")).toBeDefined();
  });

  it("setzt title auf reason wenn vorhanden", () => {
    render(<ProviderHealthBadge status="unavailable" reason="HF_TOKEN fehlt" />);
    const badge = screen.getByTitle("HF_TOKEN fehlt");
    expect(badge).toBeDefined();
  });
});
