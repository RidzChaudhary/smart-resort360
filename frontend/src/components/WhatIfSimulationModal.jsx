import React, { useState } from 'react';
import {
  X,
  Sliders,
  Play,
  RotateCcw,
  CloudRain,
  Wind,
  Droplets,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Building,
  Users
} from 'lucide-react';
import { digitalTwinAPI } from '../services/api';

export const WhatIfSimulationModal = ({
  isOpen,
  onClose,
  currentWeather,
  onApplySimulation,
  onResetSimulation,
  isSimulationActive
}) => {
  const [rainProb, setRainProb] = useState(85);
  const [rainIntensity, setRainIntensity] = useState(8.5);
  const [windSpeed, setWindSpeed] = useState(38);
  const [duration, setDuration] = useState(4);
  const [loading, setLoading] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);

  if (!isOpen) return null;

  const handlePreset = (type) => {
    if (type === 'storm') {
      setRainProb(87);
      setRainIntensity(12.0);
      setWindSpeed(45);
      setDuration(4);
    } else if (type === 'moderate') {
      setRainProb(55);
      setRainIntensity(3.5);
      setWindSpeed(22);
      setDuration(2);
    } else if (type === 'clear') {
      setRainProb(10);
      setRainIntensity(0);
      setWindSpeed(12);
      setDuration(1);
    }
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const res = await digitalTwinAPI.simulate({
        rain_probability: Number(rainProb),
        rain_intensity_mm: Number(rainIntensity),
        wind_speed_kmh: Number(windSpeed),
        duration_hours: Number(duration)
      });
      setSimulationResult(res.data);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (simulationResult && onApplySimulation) {
      onApplySimulation(simulationResult);
      onClose();
    }
  };

  const handleReset = () => {
    if (onResetSimulation) {
      onResetSimulation();
    }
    setSimulationResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white border border-ivory-300 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
        {/* Modal Header */}
        <div className="p-5 border-b border-ivory-300 flex items-center justify-between bg-ivory-50/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-forest-50 border border-forest-200 text-forest-800 shadow-sm">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-forest-900">Digital Twin What-If Simulator</h2>
              <p className="text-xs text-charcoal-600">
                Simulate hypothetical weather scenarios non-destructively without modifying production data
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-charcoal-500 hover:text-charcoal-900 hover:bg-ivory-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Preset Buttons */}
          <div>
            <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2.5">
              Quick Scenario Presets
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => handlePreset('storm')}
                className="px-3.5 py-2.5 text-xs rounded-xl border border-red-200 bg-status-criticalBg hover:bg-red-100 text-left transition shadow-sm"
              >
                <div className="font-extrabold text-status-criticalText mb-0.5">⛈️ Severe Storm</div>
                <div className="text-[11px] text-red-800">87% rain, 45km/h wind</div>
              </button>

              <button
                type="button"
                onClick={() => handlePreset('moderate')}
                className="px-3.5 py-2.5 text-xs rounded-xl border border-amber-200 bg-amber-50 hover:bg-amber-100 text-left transition shadow-sm"
              >
                <div className="font-extrabold text-amber-900 mb-0.5">🌦️ Passing Shower</div>
                <div className="text-[11px] text-amber-800">55% rain, 22km/h wind</div>
              </button>

              <button
                type="button"
                onClick={() => handlePreset('clear')}
                className="px-3.5 py-2.5 text-xs rounded-xl border border-green-200 bg-status-successBg hover:bg-green-100 text-left transition shadow-sm"
              >
                <div className="font-extrabold text-status-successText mb-0.5">☀️ Clear Skies</div>
                <div className="text-[11px] text-emerald-800">10% rain, light breeze</div>
              </button>
            </div>
          </div>

          {/* Parameter Sliders */}
          <div className="space-y-4 bg-ivory-50/80 p-4.5 rounded-xl border border-ivory-300">
            {/* Rain Probability */}
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="flex items-center gap-1.5 text-charcoal-800 font-bold">
                  <Droplets className="w-3.5 h-3.5 text-forest-700" />
                  Simulated Rain Probability
                </span>
                <span className="font-extrabold text-forest-900 text-sm">{rainProb}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={rainProb}
                onChange={(e) => setRainProb(e.target.value)}
                className="w-full accent-forest-700 cursor-pointer h-2 bg-ivory-300 rounded-lg"
              />
            </div>

            {/* Rain Intensity */}
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="flex items-center gap-1.5 text-charcoal-800 font-bold">
                  <CloudRain className="w-3.5 h-3.5 text-sage-600" />
                  Precipitation Intensity
                </span>
                <span className="font-extrabold text-forest-900 text-sm">{rainIntensity} mm/h</span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="0.5"
                value={rainIntensity}
                onChange={(e) => setRainIntensity(e.target.value)}
                className="w-full accent-forest-700 cursor-pointer h-2 bg-ivory-300 rounded-lg"
              />
            </div>

            {/* Wind Speed */}
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="flex items-center gap-1.5 text-charcoal-800 font-bold">
                  <Wind className="w-3.5 h-3.5 text-teal-600" />
                  Wind Velocity
                </span>
                <span className="font-extrabold text-forest-900 text-sm">{windSpeed} km/h</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={windSpeed}
                onChange={(e) => setWindSpeed(e.target.value)}
                className="w-full accent-forest-700 cursor-pointer h-2 bg-ivory-300 rounded-lg"
              />
            </div>

            {/* Storm Duration */}
            <div>
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className="flex items-center gap-1.5 text-charcoal-800 font-bold">
                  <Clock className="w-3.5 h-3.5 text-brass-600" />
                  Window Duration
                </span>
                <span className="font-extrabold text-forest-900 text-sm">{duration} Hours</span>
              </div>
              <input
                type="range"
                min="1"
                max="12"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-full accent-forest-700 cursor-pointer h-2 bg-ivory-300 rounded-lg"
              />
            </div>
          </div>

          {/* Action Trigger */}
          <button
            type="button"
            onClick={handleRunSimulation}
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-forest-900 hover:bg-forest-800 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-btn transition"
          >
            <Play className="w-4 h-4 text-brass-300" />
            {loading ? 'Evaluating Digital Twin Impact...' : 'Run Simulation Analysis'}
          </button>

          {/* Simulation Output Card */}
          {simulationResult && (
            <div className="p-4.5 rounded-xl border border-forest-300 bg-forest-50/80 space-y-3 animate-fadeIn shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-forest-900 uppercase tracking-wider">
                  Simulation Impact Results
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${
                  simulationResult.impact_analysis?.risk_level === 'CRITICAL' || simulationResult.impact_analysis?.risk_level === 'HIGH'
                    ? 'bg-status-criticalBg text-status-criticalText border border-red-300'
                    : 'bg-status-successBg text-status-successText border border-green-300'
                }`}>
                  {simulationResult.impact_analysis?.risk_level} RISK
                </span>
              </div>

              <p className="text-xs text-charcoal-900 leading-relaxed font-semibold">
                {simulationResult.summary}
              </p>

              {/* Impact Breakdown Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                <div className="bg-white p-2.5 rounded-lg border border-ivory-300 text-center shadow-sm">
                  <span className="text-[10px] text-charcoal-500 font-bold uppercase">Risk Score</span>
                  <p className="text-base font-extrabold text-brass-700 mt-0.5">
                    {simulationResult.impact_analysis?.risk_score}/100
                  </p>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-ivory-300 text-center shadow-sm">
                  <span className="text-[10px] text-charcoal-500 font-bold uppercase">Events Impacted</span>
                  <p className="text-base font-extrabold text-status-criticalText mt-0.5">
                    {simulationResult.impact_analysis?.affected_events_count}
                  </p>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-ivory-300 text-center shadow-sm">
                  <span className="text-[10px] text-charcoal-500 font-bold uppercase">Guests Affected</span>
                  <p className="text-base font-extrabold text-forest-800 mt-0.5">
                    {simulationResult.impact_analysis?.affected_guests}
                  </p>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-ivory-300 text-center shadow-sm">
                  <span className="text-[10px] text-charcoal-500 font-bold uppercase">Depts Engaged</span>
                  <p className="text-base font-extrabold text-teal-700 mt-0.5">
                    {simulationResult.impact_analysis?.affected_departments?.length || 0}
                  </p>
                </div>
              </div>

              {/* Department Response requirements */}
              {simulationResult.impact_analysis?.affected_departments?.length > 0 && (
                <div className="text-xs text-charcoal-700 pt-1">
                  <span className="font-bold text-charcoal-900">Required Department Actions: </span>
                  {simulationResult.impact_analysis.affected_departments.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-5 border-t border-ivory-300 bg-ivory-50 flex items-center justify-between gap-3">
          {isSimulationActive ? (
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-white hover:bg-ivory-100 text-charcoal-700 border border-ivory-300 shadow-sm transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to Real-Time State
            </button>
          ) : <div />}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-white hover:bg-ivory-100 text-charcoal-700 border border-ivory-300 transition"
            >
              Cancel
            </button>
            {simulationResult && (
              <button
                type="button"
                onClick={handleApply}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-forest-900 hover:bg-forest-800 text-white shadow-btn transition"
              >
                Apply Scenario to Digital Twin
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
