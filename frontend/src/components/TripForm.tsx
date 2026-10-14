import { useEffect, useRef, useState, type FormEvent } from "react";
import { fetchAppConfig, geocode } from "../api";
import type { Place } from "../types";
import {
  DeparturePicker,
  defaultDepartureLocal,
  validateDeparture,
} from "./DeparturePicker";

const FALLBACK_MAX_HOURS = 168;

export interface TripFormValues {
  origin: string | Place;
  destination: string | Place;
  departure_at: string;
  load_lbs: number;
}

interface Props {
  loading: boolean;
  onSubmit: (values: TripFormValues) => void;
}

function dedupePlaces(places: Place[]): Place[] {
  const seen = new Set<string>();
  const out: Place[] = [];
  for (const p of places) {
    const key = `${p.label.trim().toLowerCase()}|${p.lat.toFixed(4)}|${p.lng.toFixed(4)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(p);
  }
  return out;
}

function PlaceInput({
  label,
  value,
  onChange,
  onSelect,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onSelect: (p: Place | null) => void;
}) {
  const [suggestions, setSuggestions] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const skipFetchRef = useRef(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (skipFetchRef.current) {
      skipFetchRef.current = false;
      setSuggestions([]);
      setOpen(false);
      return;
    }

    const q = value.trim();
    if (q.length < 3) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    const requestId = ++requestIdRef.current;
    const t = window.setTimeout(() => {
      geocode(q)
        .then((results) => {
          if (requestId !== requestIdRef.current) return;
          const unique = dedupePlaces(results);
          setSuggestions(unique);
          setOpen(unique.length > 0);
        })
        .catch(() => {
          if (requestId !== requestIdRef.current) return;
          setSuggestions([]);
          setOpen(false);
        });
    }, 450);

    return () => {
      window.clearTimeout(t);
    };
  }, [value]);

  function pickPlace(place: Place) {
    skipFetchRef.current = true;
    requestIdRef.current += 1;
    setSuggestions([]);
    setOpen(false);
    onChange(place.label);
    onSelect(place);
  }

  return (
    <label className="field">
      <span>{label}</span>
      <input
        value={value}
        onChange={(e) => {
          skipFetchRef.current = false;
          onChange(e.target.value);
          onSelect(null);
        }}
        onFocus={() => {
          if (suggestions.length > 0) setOpen(true);
        }}
        onBlur={() => {
          window.setTimeout(() => setOpen(false), 150);
        }}
        placeholder="City or address"
        autoComplete="off"
        required
      />
      {open && suggestions.length > 0 && (
        <ul className="suggest" role="listbox">
          {suggestions.map((s) => (
            <li key={`${s.lat}-${s.lng}-${s.label}`}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  pickPlace(s);
                }}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </label>
  );
}

export function TripForm({ loading, onSubmit }: Props) {
  const [originText, setOriginText] = useState("Chicago, IL");
  const [destText, setDestText] = useState("Detroit, MI");
  const [originPlace, setOriginPlace] = useState<Place | null>(null);
  const [destPlace, setDestPlace] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(defaultDepartureLocal());
  const [loadLbs, setLoadLbs] = useState(35000);
  const [dateError, setDateError] = useState<string | null>(null);
  const [maxHours, setMaxHours] = useState(FALLBACK_MAX_HOURS);
  const [guidance, setGuidance] = useState(
    "Best ETA accuracy within ~48h; planning allowed up to 7 days.",
  );

  useEffect(() => {
    fetchAppConfig()
      .then((cfg) => {
        setMaxHours(cfg.departure_max_hours_ahead);
        setGuidance(cfg.departure_guidance);
      })
      .catch(() => {});
  }, []);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const err = validateDeparture(departure, maxHours);
    if (err) {
      setDateError(err);
      return;
    }
    setDateError(null);
    const local = new Date(departure);
    onSubmit({
      origin: originPlace ?? originText,
      destination: destPlace ?? destText,
      departure_at: local.toISOString(),
      load_lbs: loadLbs,
    });
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h1 className="brand">LaneGuard</h1>
      <p className="tagline">Weather-aware truck routing</p>

      <PlaceInput
        label="Origin"
        value={originText}
        onChange={setOriginText}
        onSelect={setOriginPlace}
      />
      <PlaceInput
        label="Destination"
        value={destText}
        onChange={setDestText}
        onSelect={setDestPlace}
      />

      <DeparturePicker
        value={departure}
        maxHours={maxHours}
        error={dateError}
        guidance={guidance}
        onChange={setDeparture}
        onError={setDateError}
      />

      <label className="field">
        <span>Load weight (lb)</span>
        <input
          type="number"
          min={0}
          step={100}
          value={loadLbs}
          onChange={(e) => setLoadLbs(Number(e.target.value))}
          required
        />
      </label>

      <button className="primary" type="submit" disabled={loading}>
        {loading ? "Finding routes…" : "Find safest routes"}
      </button>
    </form>
  );
}
