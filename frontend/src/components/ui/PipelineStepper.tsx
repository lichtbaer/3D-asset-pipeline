export interface PipelineStep {
  id: string;
  label: string;
  completed: boolean;
  active: boolean;
  disabled: boolean;
  subSteps?: PipelineStep[];
}

export interface PipelineStepperProps {
  steps: PipelineStep[];
  onStepClick: (stepId: string) => void;
}

export function PipelineStepper({ steps, onStepClick }: PipelineStepperProps) {
  return (
    <nav className="pipeline-stepper" aria-label="Pipeline-Fortschritt">
      {steps.map((step, index) => {
        const stepClasses = [
          "pipeline-stepper__step",
          step.active && "pipeline-stepper__step--active",
          step.completed && "pipeline-stepper__step--completed",
          step.disabled && "pipeline-stepper__step--disabled",
        ]
          .filter(Boolean)
          .join(" ");

        const showConnector = index < steps.length - 1;
        const connectorCompleted = step.completed;

        return (
          <div key={step.id} className="pipeline-stepper__step-group">
            <div>
              <button
                type="button"
                className={stepClasses}
                onClick={() => onStepClick(step.id)}
                disabled={step.disabled}
                aria-current={step.active ? "step" : undefined}
              >
                <span className="pipeline-stepper__indicator">
                  {step.completed ? "✓" : index + 1}
                </span>
                <span className="pipeline-stepper__label">{step.label}</span>
              </button>
              {step.subSteps && step.subSteps.length > 0 && (
                <div className="pipeline-stepper__sub-steps">
                  {step.subSteps.map((sub) => (
                    <button
                      key={sub.id}
                      type="button"
                      className={`pipeline-stepper__sub-step${sub.active ? " pipeline-stepper__sub-step--active" : ""}`}
                      onClick={() => onStepClick(sub.id)}
                      disabled={sub.disabled}
                      aria-current={sub.active ? "step" : undefined}
                    >
                      {sub.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {showConnector && (
              <div
                className={`pipeline-stepper__connector${connectorCompleted ? " pipeline-stepper__connector--completed" : ""}`}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
