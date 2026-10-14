import { useEffect, useMemo, useRef, useState } from "react";

const PAST_GRACE_MS = 5 * 60 * 1000;
const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function pad(n: number) {
  return String(n).padStart(2, "0");
}

export function toLocalInputValue(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function defaultDepartureLocal(): string {
  const d = new Date();
  d.setSeconds(0, 0);
  d.setMinutes(0);
  d.setHours(d.getHours() + 1);
  return toLocalInputValue(d);
}

function splitLocal(value: string): { date: string; time: string } {
  const [date = "", time = "08:00"] = value.split("T");
  return { date, time: time.slice(0, 5) };
}

function joinLocal(date: string, time: string): string {
  return `${date}T${time || "00:00"}`;
}

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseDayKey(key: string): Date {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function formatDayChip(d: Date, today: Date): { title: string; sub: string } {
  const diff = Math.round((startOfDay(d).getTime() - startOfDay(today).getTime()) / 86400000);
  const weekday = d.toLocaleDateString(undefined, { weekday: "short" });
  const md = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  if (diff === 0) return { title: "Today", sub: md };
  if (diff === 1) return { title: "Tomorrow", sub: md };
  return { title: weekday, sub: md };
}

function readableDeparture(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "Choose a departure";
  return d.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDisplayDate(dateKey: string): string {
  if (!dateKey) return "Select date";
  const d = parseDayKey(dateKey);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDisplayTime(time: string): string {
  if (!time) return "Select time";
  const [h, m] = time.split(":").map(Number);
  const d = new Date();
  d.setHours(h || 0, m || 0, 0, 0);
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function validateDeparture(localValue: string, maxHours: number): string | null {
  const chosen = new Date(localValue);
  if (Number.isNaN(chosen.getTime())) return "Enter a valid departure date and time.";
  const now = Date.now();
  if (chosen.getTime() < now - PAST_GRACE_MS) {
    return "Departure cannot be in the past.";
  }
  if (chosen.getTime() > now + maxHours * 60 * 60 * 1000) {
    const days = maxHours / 24;
    return `Departure must be within the next ${maxHours} hours (~${days} days) for reliable weather.`;
  }
  return null;
}

function clampToWindow(d: Date, maxHours: number): Date {
  const now = new Date();
  const min = new Date(now.getTime() - PAST_GRACE_MS);
  const max = new Date(now.getTime() + maxHours * 60 * 60 * 1000);
  if (d < min) return new Date(min.getTime() + 60_000);
  if (d > max) return max;
  return d;
}

function buildTimeOptions(): string[] {
  const opts: string[] = [];
  for (let h = 0; h < 24; h += 1) {
    for (const m of [0, 15, 30, 45]) {
      opts.push(`${pad(h)}:${pad(m)}`);
    }
  }
  return opts;
}

const TIME_OPTIONS = buildTimeOptions();

function monthMatrix(view: Date): (Date | null)[][] {
  const first = new Date(view.getFullYear(), view.getMonth(), 1);
  const startPad = first.getDay();
  const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
  const cells: (Date | null)[] = [];
  for (let i = 0; i < startPad; i += 1) cells.push(null);
  for (let d = 1; d <= daysInMonth; d += 1) {
    cells.push(new Date(view.getFullYear(), view.getMonth(), d));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  const rows: (Date | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
  return rows;
}

interface Props {
  value: string;
  maxHours: number;
  error: string | null;
  guidance: string;
  onChange: (value: string) => void;
  onError: (error: string | null) => void;
}

export function DeparturePicker({
  value,
  maxHours,
  error,
  guidance,
  onChange,
  onError,
}: Props) {
  const { date, time } = splitLocal(value);
  const today = useMemo(() => new Date(), []);
  const rootRef = useRef<HTMLDivElement>(null);
  const [openPanel, setOpenPanel] = useState<"date" | "time" | null>(null);
  const [viewMonth, setViewMonth] = useState(() => parseDayKey(date || dayKey(new Date())));

  const minBound = useMemo(() => startOfDay(new Date()), []);
  const maxBound = useMemo(
    () => startOfDay(new Date(Date.now() + maxHours * 60 * 60 * 1000)),
    [maxHours],
  );

  const dayOptions = useMemo(() => {
    const days: Date[] = [];
    let cursor = startOfDay(new Date());
    while (cursor <= maxBound && days.length < 8) {
      days.push(new Date(cursor));
      cursor = new Date(cursor.getTime() + 86400000);
    }
    return days;
  }, [maxBound]);

  const presets = useMemo(() => {
    const now = new Date();
    const make = (label: string, d: Date) => ({
      label,
      value: toLocalInputValue(clampToWindow(d, maxHours)),
    });
    const tonight = new Date(now);
    tonight.setHours(20, 0, 0, 0);
    if (tonight <= now) tonight.setDate(tonight.getDate() + 1);

    const tomorrowAm = new Date(now);
    tomorrowAm.setDate(tomorrowAm.getDate() + 1);
    tomorrowAm.setHours(6, 0, 0, 0);

    const plus3 = new Date(now);
    plus3.setDate(plus3.getDate() + 3);
    plus3.setHours(8, 0, 0, 0);

    return [
      make("+1 hour", new Date(now.getTime() + 3600000)),
      make("Tonight", tonight),
      make("Tomorrow 6am", tomorrowAm),
      make("+3 days", plus3),
    ];
  }, [maxHours]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpenPanel(null);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenPanel(null);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    if (date) setViewMonth(parseDayKey(date));
  }, [date]);

  function apply(next: string) {
    onChange(next);
    onError(validateDeparture(next, maxHours));
  }

  function setDatePart(nextDate: string) {
    const merged = joinLocal(nextDate, time || "08:00");
    const clamped = toLocalInputValue(clampToWindow(new Date(merged), maxHours));
    apply(clamped);
    setOpenPanel(null);
  }

  function setTimePart(nextTime: string) {
    apply(joinLocal(date, nextTime));
    setOpenPanel(null);
  }

  function isDisabledDay(d: Date): boolean {
    const s = startOfDay(d).getTime();
    return s < minBound.getTime() || s > maxBound.getTime();
  }

  const rows = monthMatrix(viewMonth);
  const monthLabel = viewMonth.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  const canPrevMonth =
    new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1) > minBound;
  const canNextMonth =
    new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1) <= maxBound;

  return (
    <div className="departure-picker" ref={rootRef}>
      <div className="departure-picker-label">
        <span>Departure</span>
        <em>Next {Math.round(maxHours / 24)} days</em>
      </div>

      <div className="departure-summary">
        <span className="departure-summary-icon" aria-hidden>
          ▣
        </span>
        <div>
          <strong>{readableDeparture(value)}</strong>
          <p>Used for ETA weather at every checkpoint</p>
        </div>
      </div>

      <div className="day-chip-row" role="listbox" aria-label="Departure day">
        {dayOptions.map((d) => {
          const key = dayKey(d);
          const active = key === date;
          const { title, sub } = formatDayChip(d, today);
          return (
            <button
              key={key}
              type="button"
              role="option"
              aria-selected={active}
              className={`day-chip ${active ? "active" : ""}`}
              onClick={() => setDatePart(key)}
            >
              <span>{title}</span>
              <small>{sub}</small>
            </button>
          );
        })}
      </div>

      <div className="departure-fields">
        <div className={`picker-field ${openPanel === "date" ? "open" : ""}`}>
          <span className="picker-field-label">Date</span>
          <button
            type="button"
            className="picker-trigger"
            aria-haspopup="dialog"
            aria-expanded={openPanel === "date"}
            onClick={() => setOpenPanel((p) => (p === "date" ? null : "date"))}
          >
            <span>{formatDisplayDate(date)}</span>
            <em>▾</em>
          </button>
          {openPanel === "date" && (
            <div className="picker-popover calendar-popover" role="dialog" aria-label="Choose date">
              <div className="cal-nav">
                <button
                  type="button"
                  className="cal-nav-btn"
                  disabled={!canPrevMonth}
                  onClick={() =>
                    setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1, 1))
                  }
                >
                  ‹
                </button>
                <strong>{monthLabel}</strong>
                <button
                  type="button"
                  className="cal-nav-btn"
                  disabled={!canNextMonth}
                  onClick={() =>
                    setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1))
                  }
                >
                  ›
                </button>
              </div>
              <div className="cal-weekdays">
                {WEEKDAYS.map((w) => (
                  <span key={w}>{w}</span>
                ))}
              </div>
              <div className="cal-grid">
                {rows.flatMap((row, ri) =>
                  row.map((cell, ci) => {
                    if (!cell) {
                      return <span key={`e-${ri}-${ci}`} className="cal-day empty" />;
                    }
                    const key = dayKey(cell);
                    const disabled = isDisabledDay(cell);
                    const selected = key === date;
                    const isToday = key === dayKey(today);
                    return (
                      <button
                        key={key}
                        type="button"
                        disabled={disabled}
                        className={`cal-day ${selected ? "selected" : ""} ${isToday ? "today" : ""}`}
                        onClick={() => setDatePart(key)}
                      >
                        {cell.getDate()}
                      </button>
                    );
                  }),
                )}
              </div>
            </div>
          )}
        </div>

        <div className={`picker-field ${openPanel === "time" ? "open" : ""}`}>
          <span className="picker-field-label">Time</span>
          <button
            type="button"
            className="picker-trigger"
            aria-haspopup="listbox"
            aria-expanded={openPanel === "time"}
            onClick={() => setOpenPanel((p) => (p === "time" ? null : "time"))}
          >
            <span>{formatDisplayTime(time)}</span>
            <em>▾</em>
          </button>
          {openPanel === "time" && (
            <div className="picker-popover time-popover" role="listbox" aria-label="Choose time">
              {TIME_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  role="option"
                  aria-selected={opt === time}
                  className={`time-option ${opt === time ? "selected" : ""}`}
                  onClick={() => setTimePart(opt)}
                >
                  {formatDisplayTime(opt)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="preset-row">
        {presets.map((p) => (
          <button
            key={p.label}
            type="button"
            className={`preset-chip ${value === p.value ? "active" : ""}`}
            onClick={() => {
              apply(p.value);
              setOpenPanel(null);
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {error && <p className="field-error">{error}</p>}
      <p className="field-hint">{guidance}</p>
    </div>
  );
}
