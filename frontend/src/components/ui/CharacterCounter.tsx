export interface CharacterCounterProps {
  current: number;
  minimum: number;
}

export function CharacterCounter({ current, minimum }: CharacterCounterProps) {
  const isBelow = current < minimum;
  return (
    <span className={`char-counter${isBelow ? " char-counter--below" : ""}`}>
      {current} / {minimum}
    </span>
  );
}
