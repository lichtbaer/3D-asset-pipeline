export interface InlineErrorProps {
  message: string | null;
  id?: string;
}

export function InlineError({ message, id }: InlineErrorProps) {
  if (!message) return null;
  return (
    <p className="inline-error" role="alert" id={id}>
      {message}
    </p>
  );
}
