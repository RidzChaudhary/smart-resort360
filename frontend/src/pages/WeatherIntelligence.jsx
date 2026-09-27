import React, { useEffect, useState, useCallback } from 'react';
import {
  CloudSun,
  CloudRain,
  Sun,
  Cloud,
  CloudLightning,
  Wind,
  Droplets,
  Sliders,
  RotateCcw,
  RefreshCw,
  AlertTriangle,
  Radio,
  MapPin,
  Building,
  Users,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Clock,
  Layers,
  Thermometer,
  Eye,
  Compass
} from 'lucide-react';
import { weatherAPI, digitalTwinAPI } from '../services/api';
import { WeatherWidget } from '../components/WeatherWidget';
import { WeatherImpactMap } from '../components/WeatherImpactMap';
import { WhatIfSimulationModal } from '../components/WhatIfSimulationModal';
import { DigitalTwinInspectPanel } from '../components/DigitalTwinInspectPanel';

export const WeatherIntelligence = () => {
  const [weather, setWeather] = useState(null);
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [digitalTwinState, setDigitalTwinState] = useState(null);
  const [impactAnalysis, setImpactAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSimModalOpen, setIsSimModalOpen] = useState(false);
  const [simulatedState, setSimulatedState] = useState(null);

  const fetchWeatherData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [wRes, rRes, dtRes, impRes] = await Promise.all([
        weatherAPI.getCurrent(),
        weatherAPI.getRiskAnalysis(),
        digitalTwinAPI.getState(),
        digitalTwinAPI.getImpactAnalysis()
      ]);
      setWeather(wRes.data);
      setRiskAnalysis(rRes.data);
      setDigitalTwinState(dtRes.data.digital_twin);
      setImpactAnalysis(impRes.data.impact_analysis);
    } catch (err) {
      console.error('Failed to load weather intelligence:', err);
      setError(err.response?.data?.detail || 'Weather intelligence telemetry could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWeatherData();
  }, [fetchWeatherData]);

  const handleApplySimulation = (simResult) => {
    setSimulatedState(simResult);
    setIsSimModalOpen(false);
  };

  const handleResetSimulation = () => {
    setSimulatedState(null);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
      </div>
    );
  }

  // Active state derived from simulated state or live backend telemetry
  const activeWeather = simulatedState ? simulatedState.simulated_state.weather : weather;
  const activeImpact = simulatedState ? simulatedState.impact_analysis : impactAnalysis;
  const isSimulationActive = !!simulatedState;

  const current = activeWeather?.current || {};
  const forecast = activeWeather?.hourly_forecast || activeWeather?.forecast || [];
  const riskLevel = activeImpact?.risk_level || 'LOW';
  const riskScore = activeImpact?.risk_score ?? 0;
  const affectedGuests = activeImpact?.affected_guests ?? 0;
  const affectedEvents = activeImpact?.affected_events_count ?? 0;

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* ── Page Header ──────────────────────────────────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-forest-100 text-forest-900 border border-forest-200">
              Goa Operational Telemetry
            </span>
            <span className="text-xs font-semibold text-charcoal-500 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-red-500" />
              Azure Palm Resort, Goa (15.2993° N, 73.9876° E)
            </span>
          </div>
          <h1 className="mt-1 text-2xl md:text-3xl font-bold text-charcoal-900 flex items-center gap-3">
            <CloudSun className="w-7 h-7 text-brass-600" />
            Weather Intelligence & Digital Twin
          </h1>
          <p className="mt-1 text-sm text-charcoal-600">
            Real-time Open-Meteo telemetry, weather impact propagation, geospatial risk mapping, and what-if scenario simulations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isSimulationActive && (
            <button
              type="button"
              onClick={handleResetSimulation}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-ivory-300 rounded-lg text-xs font-semibold text-charcoal-800 hover:bg-ivory-50 shadow-sm transition"
            >
              <RotateCcw className="w-4 h-4 text-charcoal-500" /> Reset to Live
            </button>
          )}
          <button
            type="button"
            onClick={() => setIsSimModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-forest-900 hover:bg-forest-800 text-white rounded-lg text-xs font-bold shadow-btn transition"
          >
            <Sliders className="w-4 h-4 text-brass-300" /> What-If Simulator
          </button>
          <button
            type="button"
            onClick={fetchWeatherData}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-ivory-300 rounded-lg text-xs font-semibold text-charcoal-800 hover:bg-ivory-50 shadow-sm transition"
          >
            <RefreshCw className="w-4 h-4 text-forest-700" /> Refresh
          </button>
        </div>
      </header>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-800 font-medium">
          {error}
        </div>
      )}

      {/* ── Active Simulation Banner ─────────────────────────────────── */}
      {isSimulationActive && (
        <aside className="border border-amber-300 bg-amber-50 p-4 rounded-xl shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Radio className="w-5 h-5 text-amber-700 animate-pulse shrink-0" />
            <div>
              <p className="text-xs font-extrabold text-amber-900 uppercase tracking-wider">
                Active Digital Twin Simulation Scenario
              </p>
              <p className="text-xs text-amber-800 mt-0.5">
                {simulatedState.summary || 'Simulated weather state active. Production database remains unmodified.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleResetSimulation}
            className="px-3 py-1.5 bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 rounded-lg text-xs font-bold transition shadow-sm"
          >
            Exit Simulation
          </button>
        </aside>
      )}

      {/* ── Core Weather Widget & Risk Summary ────────────────────────── */}
      <WeatherWidget
        weather={activeWeather}
        riskAnalysis={riskAnalysis}
        onOpenSimulation={() => setIsSimModalOpen(true)}
        isSimulation={isSimulationActive}
        onResetSimulation={handleResetSimulation}
      />

      {/* ── Key Impact Metrics Bar ───────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="surface p-4 rounded-xl border border-ivory-300 shadow-sm">
          <span className="text-[10px] font-mono font-bold text-charcoal-500 uppercase tracking-wider">Weather Risk Score</span>
          <div className="flex items-baseline gap-2 mt-1">
            <p className={`text-2xl font-bold font-mono ${
              riskLevel === 'CRITICAL' ? 'text-red-700' : riskLevel === 'HIGH' ? 'text-amber-700' : 'text-forest-800'
            }`}>
              {riskScore}/100
            </p>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
              riskLevel === 'CRITICAL' ? 'bg-red-100 text-red-800 border-red-200' :
              riskLevel === 'HIGH' ? 'bg-amber-100 text-amber-900 border-amber-200' :
              'bg-emerald-100 text-emerald-800 border-emerald-200'
            }`}>
              {riskLevel}
            </span>
          </div>
        </div>

        <div className="surface p-4 rounded-xl border border-ivory-300 shadow-sm">
          <span className="text-[10px] font-mono font-bold text-charcoal-500 uppercase tracking-wider">Outdoor Events Affected</span>
          <p className="mt-1 text-2xl font-bold font-mono text-charcoal-900">
            {affectedEvents} {affectedEvents === 1 ? 'event' : 'events'}
          </p>
        </div>

        <div className="surface p-4 rounded-xl border border-ivory-300 shadow-sm">
          <span className="text-[10px] font-mono font-bold text-charcoal-500 uppercase tracking-wider">Guests Impacted</span>
          <p className="mt-1 text-2xl font-bold font-mono text-forest-800">
            {affectedGuests} guests
          </p>
        </div>

        <div className="surface p-4 rounded-xl border border-ivory-300 shadow-sm">
          <span className="text-[10px] font-mono font-bold text-charcoal-500 uppercase tracking-wider">Response Departments</span>
          <p className="mt-1 text-sm font-bold text-teal-800 truncate">
            {activeImpact?.affected_departments?.length ? activeImpact.affected_departments.join(', ') : 'None Required'}
          </p>
        </div>
      </div>

      {/* ── Geospatial Resort Map & Digital Twin Inspector Grid ────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Interactive Map */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-base font-bold text-charcoal-900 flex items-center gap-2">
              <Compass className="w-5 h-5 text-forest-700" />
              Geospatial Resort Weather Map
            </h2>
            <span className="text-xs text-charcoal-500 font-medium">Goa Beachfront Locations</span>
          </div>
          <WeatherImpactMap
            weatherData={activeWeather}
            impactAnalysis={activeImpact}
            digitalTwinState={digitalTwinState}
          />
        </div>

        {/* Digital Twin Operational Inspector Panel */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-base font-bold text-charcoal-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-brass-600" />
              Digital Twin Operational State Inspector
            </h2>
            <span className="text-xs text-charcoal-500 font-medium">Read-Only Virtual State</span>
          </div>
          <DigitalTwinInspectPanel
            digitalTwinState={digitalTwinState}
            impactAnalysis={activeImpact}
            isSimulationActive={isSimulationActive}
          />
        </div>
      </div>

      {/* ── 24-Hour Forecast Deck ────────────────────────────────────────────── */}
      {forecast.length > 0 && (
        <section className="surface p-6 rounded-xl border border-ivory-300 shadow-sm space-y-4">
          <h2 className="text-lg font-bold text-charcoal-900 flex items-center gap-2">
            <Clock className="w-5 h-5 text-forest-700" />
            24-Hour Weather Forecast Projections
          </h2>

          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
            {forecast.slice(0, 24).map((item, idx) => (
              <div
                key={idx}
                className="shrink-0 w-28 p-3 bg-ivory-50/80 rounded-xl border border-ivory-200 text-center space-y-1.5 shadow-sm"
              >
                <p className="text-[11px] font-bold text-charcoal-600 uppercase font-mono">
                  {item.time ? new Date(item.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `+${idx}h`}
                </p>
                <div className="py-1 flex justify-center text-forest-700">
                  {item.rain_probability >= 60 ? (
                    <CloudRain className="w-6 h-6 text-forest-600" />
                  ) : item.rain_probability >= 30 ? (
                    <Cloud className="w-6 h-6 text-sage-600" />
                  ) : (
                    <Sun className="w-6 h-6 text-brass-500" />
                  )}
                </div>
                <p className="text-sm font-bold text-charcoal-900 font-mono">
                  {item.temperature ?? current.temperature ?? 28}°C
                </p>
                <p className="text-[10px] font-semibold text-charcoal-500 flex items-center justify-center gap-1">
                  <Droplets className="w-3 h-3 text-forest-600" />
                  {item.rain_probability ?? 0}%
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── What-If Simulation Modal ─────────────────────────────────── */}
      <WhatIfSimulationModal
        isOpen={isSimModalOpen}
        onClose={() => setIsSimModalOpen(false)}
        currentWeather={weather?.current}
        onApplySimulation={handleApplySimulation}
        onResetSimulation={handleResetSimulation}
        isSimulationActive={isSimulationActive}
      />
    </main>
  );
};
