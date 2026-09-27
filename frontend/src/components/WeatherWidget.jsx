import React, { useState } from 'react';
import {
  CloudRain,
  Sun,
  Cloud,
  CloudLightning,
  Wind,
  Droplets,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Sliders,
  Radio,
  Clock,
  Zap,
  RotateCcw
} from 'lucide-react';

export const WeatherWidget = ({
  weather,
  riskAnalysis,
  onOpenSimulation,
  isSimulation = false,
  onResetSimulation
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!weather) {
    return null;
  }

  const current = weather.current || {};
  const forecast = weather.hourly_forecast || weather.forecast || [];
  const riskWindow = weather.high_risk_window || riskAnalysis?.high_risk_window;
  const isDemo = current.is_demo || weather.is_demo;
  const isStale = current.is_stale;

  const getWeatherIcon = (condition = '', code = 0) => {
    const cond = condition.toLowerCase();
    if (cond.includes('thunder') || code >= 95) return <CloudLightning className="w-9 h-9 text-amber-500" />;
    if (cond.includes('rain') || cond.includes('drizzle') || code >= 51) return <CloudRain className="w-9 h-9 text-forest-600" />;
    if (cond.includes('cloud') || code >= 2) return <Cloud className="w-9 h-9 text-sage-600" />;
    return <Sun className="w-9 h-9 text-brass-500" />;
  };

  const rainProb = current.rain_probability ?? (riskWindow ? riskWindow.rain_probability : 0);
  const isHighRisk = rainProb >= 65 || riskAnalysis?.risk_level === 'HIGH' || riskAnalysis?.risk_level === 'CRITICAL';

  return (
    <div className={`rounded-xl border transition-all duration-300 shadow-card ${
      isSimulation
        ? 'bg-amber-50/90 border-amber-300 ring-2 ring-amber-200'
        : isHighRisk
        ? 'bg-red-50/80 border-red-300 ring-1 ring-red-200'
        : 'bg-white border-ivory-300'
    } p-5`}>
      {/* Top Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-ivory-200">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-forest-50 border border-forest-200 text-forest-900">
            <Radio className="w-3.5 h-3.5 text-forest-700 animate-pulse" />
            {isSimulation ? 'SIMULATED WEATHER SCENARIO' : isDemo ? 'WEATHER SIGNAL (DEMO DATA)' : isStale ? `CACHED WEATHER · ${current.data_age_minutes || 0} MIN OLD` : 'LIVE OPEN-METEO TELEMETRY'}
          </div>
          {isHighRisk && (
            <span className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-status-criticalBg border border-red-300 text-status-criticalText animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5" />
              HIGH OPERATIONAL RISK DETECTED
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isSimulation && onResetSimulation && (
            <button
              onClick={onResetSimulation}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white hover:bg-ivory-100 text-charcoal-700 border border-ivory-300 shadow-sm transition"
            >
              <RotateCcw className="w-3.5 h-3.5 text-charcoal-500" />
              Reset to Live
            </button>
          )}
          <button
            onClick={onOpenSimulation}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg bg-forest-900 hover:bg-forest-800 text-white shadow-btn transition hover:scale-[1.02] active:scale-[0.98]"
          >
            <Sliders className="w-3.5 h-3.5 text-brass-300" />
            What-If Simulator
          </button>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
        {/* Current Condition & Temp */}
        <div className="flex items-center gap-4 bg-ivory-50/70 p-3.5 rounded-xl border border-ivory-200">
          <div className="p-3 bg-white rounded-xl border border-ivory-300 shadow-sm flex items-center justify-center">
            {getWeatherIcon(current.condition, current.weather_code)}
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-charcoal-900">
                {current.temperature_c ?? '--'}°
              </span>
              <span className="text-charcoal-500 font-bold text-sm">C</span>
            </div>
            <p className="text-xs font-bold text-charcoal-800 mt-0.5">{current.condition || 'Unknown'}</p>
          </div>
        </div>

        {/* Rain Probability Metric */}
        <div className="bg-ivory-50/70 border border-ivory-200 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-charcoal-600 mb-1.5">
            <span className="flex items-center gap-1 font-bold text-charcoal-800">
              <Droplets className="w-3.5 h-3.5 text-forest-700" />
              Precipitation Probability
            </span>
            <span className={`font-extrabold text-sm ${rainProb >= 70 ? 'text-status-criticalText' : rainProb >= 40 ? 'text-brass-700' : 'text-forest-900'}`}>
              {rainProb}%
            </span>
          </div>
          <div className="w-full bg-ivory-300 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                rainProb >= 70 ? 'bg-status-critical' : rainProb >= 40 ? 'bg-brass-500' : 'bg-forest-600'
              }`}
              style={{ width: `${Math.min(rainProb, 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-charcoal-500 font-medium mt-2">
            Rain volume: <span className="text-charcoal-800 font-semibold">{current.precipitation_mm ?? 0} mm/h</span>
          </p>
        </div>

        {/* Wind Metric */}
        <div className="bg-ivory-50/70 border border-ivory-200 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-charcoal-600 mb-1.5">
            <span className="flex items-center gap-1 font-bold text-charcoal-800">
              <Wind className="w-3.5 h-3.5 text-sage-600" />
              Wind Velocity
            </span>
            <span className="font-extrabold text-sm text-charcoal-900">
              {current.wind_speed_kmh ?? '--'}{current.wind_speed_kmh != null ? ' km/h' : ''}
            </span>
          </div>
          <div className="w-full bg-ivory-300 rounded-full h-2.5 overflow-hidden">
            <div
              className="h-full bg-sage-500 transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(((current.wind_speed_kmh || 0) / 80) * 100, 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-charcoal-500 font-medium mt-2">
            Max gusts: <span className="text-charcoal-800 font-semibold">{current.wind_gusts_kmh ?? '--'}{current.wind_gusts_kmh != null ? ' km/h' : ''}</span>
          </p>
        </div>

        {/* Operational Risk Assessment Banner */}
        <div className={`rounded-xl p-3.5 border ${
          isHighRisk
            ? 'bg-status-criticalBg border-red-200 text-status-criticalText'
            : 'bg-forest-50/80 border-forest-200 text-forest-900'
        }`}>
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-1">
            <Zap className={`w-3.5 h-3.5 ${isHighRisk ? 'text-status-critical' : 'text-forest-700'}`} />
            Operational Advisory
          </div>
          <p className="text-xs leading-relaxed font-medium">
            {riskAnalysis?.recommendation || (isHighRisk
              ? 'High rain probability detected. Outdoor events require indoor backup preparation.'
              : 'Weather risk assessment is unavailable. Confirm local conditions before outdoor operations.')}
          </p>
        </div>
      </div>

      {/* Hourly Forecast Dropdown Toggle */}
      {forecast.length > 0 && (
        <div className="mt-4 pt-3 border-t border-ivory-200">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between text-xs font-bold text-charcoal-700 hover:text-forest-900 transition"
          >
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-forest-700" />
              24-Hour Forecast Timeline & Hourly Precipitation Rates
            </span>
            <span className="flex items-center gap-1 text-forest-700 font-bold">
              {expanded ? 'Hide 24h Timeline' : 'View 24h Timeline'}
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </span>
          </button>

          {expanded && (
            <div className="mt-3 grid grid-cols-4 sm:grid-cols-6 md:grid-cols-12 gap-2 overflow-x-auto pb-2">
              {forecast.slice(0, 12).map((hour, idx) => {
                const hourProb = hour.rain_probability ?? 0;
                const hourTime = hour.time ? new Date(hour.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `+${idx}h`;
                const isHourCritical = hourProb >= 70;

                return (
                  <div
                    key={idx}
                    className={`flex flex-col items-center p-2 rounded-lg border text-center transition ${
                      isHourCritical
                        ? 'bg-status-criticalBg border-red-300 text-status-criticalText'
                        : 'bg-ivory-50 border-ivory-300 text-charcoal-800'
                    }`}
                  >
                    <span className="text-[10px] text-charcoal-500 font-bold font-mono">{hourTime}</span>
                    <span className="text-xs font-extrabold my-1">{hour.temperature_c ?? 25}°</span>
                    <Droplets className={`w-3 h-3 ${isHourCritical ? 'text-status-critical' : 'text-forest-700'}`} />
                    <span className={`text-[10px] font-bold mt-0.5 ${isHourCritical ? 'text-status-criticalText' : 'text-forest-800'}`}>
                      {hourProb}%
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
