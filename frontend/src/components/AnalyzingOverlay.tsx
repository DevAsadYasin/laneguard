import { useEffect, useState } from "react";

const FRIENDLY_LINES = [
  "Looking for the right lane for you…",
  "Checking the skies along the way…",
  "Weighing the safer options…",
  "Sniffing out clear corridors…",
  "Matching weather to your departure…",
  "Comparing a few good paths…",
  "Almost there — lining up your routes…",
  "Putting the finishing shine on this…",
];

interface Props {
  active: boolean;
}

export function AnalyzingOverlay({ active }: Props) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setIndex(0);
      return;
    }
    const id = window.setInterval(() => {
      setIndex((i) => {
        if (i >= FRIENDLY_LINES.length - 1) return i;
        return i + 1;
      });
    }, 2400);
    return () => window.clearInterval(id);
  }, [active]);

  if (!active) return null;

  return (
    <div className="analyzing-overlay" role="status" aria-live="polite">
      <div className="analyzing-card">
        <div className="analyzing-spinner" aria-hidden />
        <p className="analyzing-eyebrow">Loading</p>
        <h2 className="analyzing-title">Finding your safest path…</h2>
        <p className="analyzing-status" key={index}>
          {FRIENDLY_LINES[index]}
        </p>
      </div>
    </div>
  );
}
