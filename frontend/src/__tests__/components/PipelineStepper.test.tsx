import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  PipelineStepper,
  type PipelineStep,
} from "../../components/ui/PipelineStepper.js";

describe("PipelineStepper", () => {
  const baseSteps: PipelineStep[] = [
    { id: "a", label: "Schritt A", completed: false, active: true, disabled: false },
    { id: "b", label: "Schritt B", completed: false, active: false, disabled: false },
  ];

  it("ruft onStepClick mit stepId auf", async () => {
    const user = userEvent.setup();
    const onStepClick = vi.fn();
    render(<PipelineStepper steps={baseSteps} onStepClick={onStepClick} />);

    await user.click(screen.getByRole("button", { name: /Schritt B/i }));
    expect(onStepClick).toHaveBeenCalledWith("b");
  });

  it("deaktivierte Schritte lösen keinen Klick aus", async () => {
    const user = userEvent.setup();
    const onStepClick = vi.fn();
    const steps: PipelineStep[] = [
      { id: "x", label: "X", completed: false, active: false, disabled: true },
    ];
    render(<PipelineStepper steps={steps} onStepClick={onStepClick} />);

    await user.click(screen.getByRole("button", { name: /X/i }));
    expect(onStepClick).not.toHaveBeenCalled();
  });
});
