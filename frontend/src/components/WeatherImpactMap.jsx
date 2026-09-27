import React, { useState } from 'react';
import {
  MapPin,
  Layers,
  CloudRain,
  ShieldAlert,
  ArrowRight,
  Users,
  Building,
  CheckCircle2,
  AlertTriangle,
  Compass,
  Maximize2,
  Eye,
  Info,
  X
} from 'lucide-react';

export const WeatherImpactMap = ({
  events = [],
  impactAnalysis = null,
  isSimulation = false,
  weather = null,
  onRelocateEvent
}) => {
  const [selectedPin, setSelectedPin] = useState(null);
  const [showRadar, setShowRadar] = useState(true);

  // Resort locations layout coordinates (% across canvas)
  const defaultLocations = [
    {
      id: 'loc_pool',
      name: 'Outdoor Pool Deck',
      type: 'OUTDOOR',
      x: 32,
      y: 42,
      capacity: 80,
      description: 'Main outdoor resort pool with patio seating & wet bar'
    },
    {
      id: 'loc_ballroom',
      name: 'Palm Ballroom',
      type: 'INDOOR',
      x: 68,
      y: 38,
      capacity: 80,
      description: 'Grand indoor climate-controlled ballroom and banquet space'
    },
    {
      id: 'loc_beach',
      name: 'Beachside Restaurant',
      type: 'OUTDOOR',
      x: 22,
      y: 72,
      capacity: 60,
      description: 'Open-air oceanfront dining and terrace'
    },
    {
      id: 'loc_garden',
      name: 'Garden Pavilion',
      type: 'OUTDOOR',
      x: 48,
      y: 26,
      capacity: 50,
      description: 'Lush landscaped garden with partial pergola cover'
    },
    {
      id: 'loc_conf',
      name: 'Ocean View Conference',
      type: 'INDOOR',
      x: 75,
      y: 65,
      capacity: 50,
      description: 'Indoor meeting suite overlooking the coastal shoreline'
    },
    {
      id: 'loc_lobby',
      name: 'Main Grand Lobby',
      type: 'INDOOR',
      x: 52,
      y: 58,
      capacity: 100,
      description: 'Central guest reception & lounge area'
    }
  ];

  const rainProb = weather?.current?.rain_probability ?? (impactAnalysis?.risk_score ?? 0);
  const isHighRisk = rainProb >= 65 || impactAnalysis?.risk_level === 'HIGH' || impactAnalysis?.risk_level === 'CRITICAL';

  return (
    <div className="surface overflow-hidden shadow-card border border-ivory-300">
      {/* Map Control Header */}
      <div className="px-5 py-3.5 bg-white border-b border-ivory-300 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-forest-50 border border-forest-200 text-forest-700">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-charcoal-900">Digital Twin Geospatial Impact Map</h3>
              {isSimulation ? (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  SIMULATED IMPACT ZONE
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-forest-50 text-forest-800 border border-forest-200">
                  REAL-TIME TWIN
                </span>
              )}
            </div>
            <p className="text-xs text-charcoal-600">Interactive venue zones, active schedules & automated relocation vectors</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => setShowRadar(!showRadar)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-semibold transition ${
              showRadar
                ? 'bg-forest-50 border-forest-300 text-forest-900 shadow-sm'
                : 'bg-white border-ivory-300 text-charcoal-600 hover:bg-ivory-100'
            }`}
          >
            <CloudRain className="w-3.5 h-3.5 text-forest-700" />
            Weather Radar Layer: {showRadar ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Main Map Visual Canvas */}
      <div className="relative w-full h-[400px] sm:h-[460px] bg-[#1a2e28] overflow-hidden select-none">
        {/* Background Grid & Architectural Floorplan Accents */}
        <div className="absolute inset-0 opacity-15 bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] bg-[size:32px_32px]" />

        {/* Coastline Shore Gradient */}
        <div className="absolute left-0 top-0 bottom-0 w-1/4 bg-gradient-to-r from-teal-900/60 via-teal-950/30 to-transparent pointer-events-none" />
        <div className="absolute left-3 top-4 text-[10px] font-extrabold text-teal-300/60 uppercase tracking-widest pointer-events-none">
          Pacific Shoreline
        </div>

        {/* Animated Weather Radar Sweep Effect */}
        {showRadar && isHighRisk && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute -inset-[50%] bg-[radial-gradient(circle_at_32%_42%,rgba(239,68,68,0.25)_0%,rgba(245,158,11,0.15)_30%,transparent_65%)] animate-pulse" />
            <div className="absolute inset-0 bg-[conic-gradient(from_0deg_at_50%_50%,rgba(255,255,255,0.12)_0deg,transparent_45deg,transparent_360deg)] animate-[spin_8s_linear_infinite]" />
          </div>
        )}

        {/* Relocation Vector Line (Between Outdoor Pool & Palm Ballroom) */}
        {isHighRisk && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
            <defs>
              <linearGradient id="relocateGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#f87171" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
            <path
              d="M 32% 42% Q 50% 25% 68% 38%"
              fill="none"
              stroke="url(#relocateGrad)"
              strokeWidth="3"
              strokeDasharray="6 4"
            />
          </svg>
        )}

        {/* Render Locations on Map */}
        {defaultLocations.map((loc) => {
          const isPool = loc.id === 'loc_pool';
          const isBallroom = loc.id === 'loc_ballroom';
          const hasEvent = isPool;
          const isTargetedByRisk = isPool && isHighRisk;
          const isAlternativeTarget = isBallroom && isHighRisk;

          return (
            <div
              key={loc.id}
              onClick={() => setSelectedPin(loc)}
              style={{ left: `${loc.x}%`, top: `${loc.y}%` }}
              className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group z-20 transition-transform duration-200 hover:scale-110"
            >
              {/* Pulsing Ripple if at risk */}
              {isTargetedByRisk && (
                <div className="absolute -inset-3 rounded-full bg-red-500/40 animate-ping pointer-events-none" />
              )}
              {isAlternativeTarget && (
                <div className="absolute -inset-3 rounded-full bg-emerald-500/40 animate-pulse pointer-events-none" />
              )}

              {/* Pin Bubble */}
              <div className={`px-3 py-1.5 rounded-xl flex items-center gap-2 border shadow-xl backdrop-blur-md transition ${
                isTargetedByRisk
                  ? 'bg-red-950/95 border-red-400 text-white ring-2 ring-red-500/60'
                  : isAlternativeTarget
                  ? 'bg-emerald-950/95 border-emerald-400 text-white ring-2 ring-emerald-500/60'
                  : loc.type === 'INDOOR'
                  ? 'bg-slate-900/95 border-slate-600 text-white'
                  : 'bg-forest-900/95 border-forest-600 text-white'
              }`}>
                <MapPin className={`w-4 h-4 flex-shrink-0 ${
                  isTargetedByRisk
                    ? 'text-red-400 animate-bounce'
                    : isAlternativeTarget
                    ? 'text-emerald-400'
                    : loc.type === 'INDOOR'
                    ? 'text-sage-400'
                    : 'text-amber-400'
                }`} />
                <div className="text-left">
                  <p className="text-xs font-bold leading-tight text-white">{loc.name}</p>
                  <p className="text-[10px] text-slate-300 mt-0.5">
                    {hasEvent ? '60 Guests Scheduled' : `${loc.type} · Cap: ${loc.capacity}`}
                  </p>
                </div>
              </div>

              {/* Status Tag for Special Nodes */}
              {isTargetedByRisk && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1.5 whitespace-nowrap px-2 py-0.5 bg-red-600 text-white text-[9px] font-extrabold rounded shadow-md uppercase tracking-wider">
                  ⚠️ Relocation Recommended
                </div>
              )}
              {isAlternativeTarget && (
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1.5 whitespace-nowrap px-2 py-0.5 bg-emerald-600 text-white text-[9px] font-extrabold rounded shadow-md uppercase tracking-wider">
                  ✓ Designated Backup Venue
                </div>
              )}
            </div>
          );
        })}

        {/* Map Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-slate-950/90 border border-slate-700/80 rounded-lg p-2.5 text-[11px] text-slate-200 backdrop-blur-md z-20 space-y-1 shadow-lg">
          <div className="font-bold text-white text-xs mb-1">Resort Map Legend</div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-slate-200 font-medium">Weather Risk Hotspot</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-200 font-medium">Indoor Backup Alternative</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span className="text-slate-200 font-medium">Outdoor Resort Amenity</span>
          </div>
        </div>

        {/* Active Scenario Card Overlay */}
        {isHighRisk && (
          <div className="absolute top-3 right-3 max-w-xs bg-slate-950/95 border border-red-500/60 rounded-xl p-3.5 shadow-2xl backdrop-blur-md z-20">
            <div className="flex items-center gap-1.5 text-xs font-bold text-red-400 mb-1">
              <ShieldAlert className="w-4 h-4" />
              Live Impact Detection
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              <span className="font-bold text-white">Sunset Pool BBQ</span> (60 guests) is scheduled outdoors during a <span className="text-red-400 font-bold">{rainProb}% rain window</span>.
            </p>
            <div className="mt-2.5 p-2 bg-charcoal-900 rounded-lg border border-charcoal-700 flex items-center justify-between text-xs">
              <div>
                <p className="text-[10px] text-ivory-300 font-semibold">Recommended Contingency:</p>
                <p className="font-bold text-emerald-400">Move to Palm Ballroom (Cap: 80)</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Selected Location Detail Drawer */}
      {selectedPin && (
        <div className="p-4 bg-white border-t border-ivory-300 flex flex-wrap items-center justify-between gap-4 animate-fadeIn">
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-bold text-charcoal-900 text-sm">{selectedPin.name}</h4>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-ivory-200 text-charcoal-800 border border-ivory-300">
                {selectedPin.type}
              </span>
              <span className="text-xs font-medium text-charcoal-600">Max Capacity: {selectedPin.capacity}</span>
            </div>
            <p className="text-xs text-charcoal-600 mt-1">{selectedPin.description}</p>
          </div>
          <button
            onClick={() => setSelectedPin(null)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-ivory-100 hover:bg-ivory-200 border border-ivory-300 rounded-lg text-charcoal-700 transition"
          >
            <X className="w-3.5 h-3.5" />
            Close
          </button>
        </div>
      )}
    </div>
  );
};
