import { useState, useCallback, useMemo } from "react";

export interface FieldRule {
  validate: (value: string) => boolean;
  message: string;
}

export interface UseFormValidationReturn {
  touchField: (name: string) => void;
  getError: (name: string, value: string) => string | null;
  isFormValid: (values: Record<string, string>) => boolean;
  showErrors: boolean;
  handleSubmitAttempt: () => void;
}

export function useFormValidation(
  fields: Record<string, FieldRule>
): UseFormValidationReturn {
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [showErrors, setShowErrors] = useState(false);

  const touchField = useCallback((name: string) => {
    setTouched((prev) => {
      if (prev.has(name)) return prev;
      const next = new Set(prev);
      next.add(name);
      return next;
    });
  }, []);

  const getError = useCallback(
    (name: string, value: string): string | null => {
      const rule = fields[name];
      if (!rule) return null;
      if (!showErrors && !touched.has(name)) return null;
      return rule.validate(value) ? null : rule.message;
    },
    [fields, touched, showErrors]
  );

  const isFormValid = useCallback(
    (values: Record<string, string>): boolean => {
      return Object.entries(fields).every(([name, rule]) =>
        rule.validate(values[name] ?? "")
      );
    },
    [fields]
  );

  const handleSubmitAttempt = useCallback(() => {
    setShowErrors(true);
    setTouched(new Set(Object.keys(fields)));
  }, [fields]);

  return useMemo(
    () => ({ touchField, getError, isFormValid, showErrors, handleSubmitAttempt }),
    [touchField, getError, isFormValid, showErrors, handleSubmitAttempt]
  );
}
