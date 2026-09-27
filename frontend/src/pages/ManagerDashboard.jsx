import React, { useState, useEffect } from 'react';
import {
  dashboardAPI,
  recommendationsAPI,
  departmentsAPI,
  weatherAPI,
  digitalTwinAPI,
  demoAPI
} from '../services/api';
import { RecommendationCard } from '../components/RecommendationCard';
import { Toast } from '../components/Toast';
import { WeatherWidget } from '../components/WeatherWidget';
import { WeatherImpactMap } from '../components/WeatherImpactMap';
import { WhatIfSimulationModal } from '../components/WhatIfSimulationModal';
import { DigitalTwinInspectPanel } from '../components/DigitalTwinInspectPanel';
import {
  Activity,
  AlertTriangle,
  Bed,
  Calendar,
  Sparkles,
  TrendingUp,
  Users,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Compass,
  Sliders,
  Clock,
  ShieldAlert
} from 'lucide-react';
import { formatDateTime } from '../utils/helpers';
import { getDepartmentNameForCategory, getDepartmentNameForRecommendation, matchesDepartment } from '../utils/departments';

export const ManagerDashboard = () => {
  const [data, setData] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('pending'); // pending | all
  const [activeQueue, setActiveQueue] = useState('overdue_tasks');
  const [notification, setNotification] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [selectedDepartment, setSelectedDepartment] = useState('all');

  // Phase 1: Real-time Weather & Digital Twin states
  const [weatherData, setWeatherData] = useState(null);
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [digitalTwinSnapshot, setDigitalTwinSnapshot] = useState(null);
  const [impactAnalysis, setImpactAnalysis] = useState(null);
  const [isSimulationModalOpen, setIsSimulationModalOpen] = useState(false);
  const [simulatedState, setSimulatedState] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [
        dashRes,
        recRes,
        departmentsRes,
        weatherRes,
        riskRes,
        twinRes,
        impactRes
      ] = await Promise.all([
        dashboardAPI.getManager(),
        recommendationsAPI.getAll(),
        departmentsAPI.getAll(),
        weatherAPI.getSnapshot().catch(() => ({ data: null })),
        weatherAPI.getRiskAnalysis().catch(() => ({ data: null })),
        digitalTwinAPI.getOperationalSnapshot().catch(() => ({ data: null })),
        digitalTwinAPI.getImpactAnalysis().catch(() => ({ data: null }))
      ]);

      setData(dashRes.data);
      setRecommendations(recRes.data);
      setDepartments(departmentsRes.data);
      setWeatherData(weatherRes?.data);
      setRiskAnalysis(riskRes?.data);
      setDigitalTwinSnapshot(twinRes?.data);
      setImpactAnalysis(impactRes?.data?.impact_analysis);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id) => {
    setProcessing(true);
    try {
      await recommendationsAPI.approve(id);
      await fetchData();
      setNotification({
        type: 'success',
        message: 'Recommendation approved. A department action is ready for assignment.'
      });
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to approve: ' + (err.response?.data?.detail || err.message)
      });
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async (id) => {
    setProcessing(true);
    try {
      await recommendationsAPI.reject(id, { action: 'REJECT', modified_notes: 'Manager declined recommendation' });
      await fetchData();
      setNotification({ type: 'success', message: 'Recommendation rejected.' });
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to reject: ' + (err.response?.data?.detail || err.message)
      });
    } finally {
      setProcessing(false);
    }
  };

  const handleModify = async (id, modifyData) => {
    setProcessing(true);
    try {
      await recommendationsAPI.modify(id, modifyData);
      await fetchData();
      setNotification({ type: 'success', message: 'Modified recommendation approved and executed.' });
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to modify: ' + (err.response?.data?.detail || err.message)
      });
    } finally {
      setProcessing(false);
    }
  };

  // What-If Simulation Handlers
  const handleApplySimulation = (simResult) => {
    setSimulatedState(simResult);
    setNotification({
      type: 'success',
      message: `Digital Twin simulation active: ${simResult.impact_analysis?.risk_level} risk scenario applied.`
    });
  };

  const handleResetSimulation = () => {
    setSimulatedState(null);
    setNotification({
      type: 'info',
      message: 'Digital Twin restored to live operational state.'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
          <p className="text-sm font-medium text-charcoal-600">Loading Resort 360 Operations...</p>
        </div>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const queues = data?.attention_queues || {};
  const queueLabels = {
    overdue_tasks: 'Overdue Tasks',
    blocked_tasks: 'Blocked Tasks',
    escalated_tasks: 'Escalated Tasks',
    critical_tasks: 'Critical Tasks',
    guest_issues: 'Guest Issues',
    inventory_risks: 'Inventory Risks',
  };
  const activeQueueItems = queues[activeQueue] || [];
  const departmentMatchesItem = (item) => matchesDepartment(
    item.department || getDepartmentNameForCategory(item.category || item.request_type),
    selectedDepartment
  );
  const filteredQueueItems = activeQueueItems.filter(departmentMatchesItem);
  const filteredRecommendations = recommendations.filter((recommendation) => matchesDepartment(
    getDepartmentNameForRecommendation(recommendation),
    selectedDepartment
  ));
  const pending = filteredRecommendations.filter(r => r.status === 'PENDING');
  const displayRecs = activeTab === 'pending' ? pending : filteredRecommendations;

  // Active weather & impact based on whether simulation is running
  const activeWeather = simulatedState ? simulatedState.simulated_state.weather : weatherData;
  const activeImpact = simulatedState ? simulatedState.impact_analysis : impactAnalysis;
  const isSimulationActive = !!simulatedState;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 bg-ivory-100 text-charcoal-900">
      <Toast
        message={notification?.message}
        type={notification?.type}
        onDismiss={() => setNotification(null)}
      />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-ivory-300">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-forest-900 mb-1 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-brass-50 border border-brass-200 flex items-center justify-center shadow-card">
              <Activity className="w-6 h-6 text-brass-700" />
            </span>
            Manager Command Center
          </h1>
          <p className="text-sm text-charcoal-600">
            Real-time resort telemetry, Digital Twin geospatial simulation, and actionable decision queues
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-white hover:bg-ivory-200 text-charcoal-700 border border-ivory-300 shadow-sm transition"
          >
            <RefreshCw className="w-3.5 h-3.5 text-forest-700" />
            Refresh Telemetry
          </button>
        </div>
      </div>


      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="surface p-5">
          <div className="flex items-center justify-between mb-2">
            <Bed className="w-5 h-5 text-forest-700" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-charcoal-500">TODAY</span>
          </div>
          <p className="text-3xl font-bold text-forest-900">{kpis.current_occupancy_pct}%</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">
            {kpis.occupied_rooms}/{kpis.total_rooms} rooms occupied
          </p>
        </div>

        <div className="surface p-5">
          <div className="flex items-center justify-between mb-2">
            <Calendar className="w-5 h-5 text-sage-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-charcoal-500">TOMORROW</span>
          </div>
          <p className="text-3xl font-bold text-forest-900">{kpis.tomorrow_check_ins}</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">Expected arrivals</p>
        </div>

        <div className="surface p-5">
          <div className="flex items-center justify-between mb-2">
            <Sparkles className="w-5 h-5 text-brass-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-charcoal-500">AI INSIGHTS</span>
          </div>
          <p className="text-3xl font-bold text-forest-900">{kpis.pending_recommendations}</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">Pending recommendations</p>
        </div>

        <div className="surface p-5">
          <div className="flex items-center justify-between mb-2">
            <AlertTriangle className="w-5 h-5 text-status-criticalText" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-charcoal-500">OPEN RISKS</span>
          </div>
          <p className="text-3xl font-bold text-status-criticalText">{kpis.critical_tasks}</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">Critical or high-priority tasks</p>
        </div>
      </div>

      {/* PHASE 1: Digital Twin Geospatial Impact Map */}
      <WeatherImpactMap
        events={digitalTwinSnapshot?.events || []}
        impactAnalysis={activeImpact}
        isSimulation={isSimulationActive}
        weather={activeWeather}
      />

      {/* PHASE 1: Collapsible Digital Twin Snapshot State Inspector */}
      <DigitalTwinInspectPanel
        snapshot={digitalTwinSnapshot}
        isSimulation={isSimulationActive}
      />

      {/* Manager attention queue */}
      <section className="surface p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-charcoal-900">Today's Operations Queue</h2>
            <p className="text-xs text-charcoal-600 mt-0.5">Tasks and signals requiring managerial decision, assignment, or follow-up.</p>
          </div>
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-forest-50 text-forest-800 border border-forest-200">
            Operations Queue
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            ['overdue_tasks', 'Overdue tasks', kpis.overdue_tasks, 'text-status-criticalText'],
            ['blocked_tasks', 'Blocked', kpis.blocked_tasks, 'text-status-warningText'],
            ['escalated_tasks', 'Escalated', kpis.escalated_tasks, 'text-status-criticalText'],
            ['critical_tasks', 'Critical tasks', kpis.critical_tasks, 'text-status-criticalText'],
            ['guest_issues', 'Guest issues', kpis.open_guest_issues, 'text-forest-800'],
            ['inventory_risks', 'Inventory risks', kpis.inventory_risks, 'text-brass-700']
          ].map(([key, label, value, color]) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveQueue(key)}
              className={`text-left bg-ivory-50 border rounded-xl p-3.5 transition ${
                activeQueue === key
                  ? 'border-forest-700 bg-white ring-2 ring-forest-200 shadow-sm'
                  : 'border-ivory-300 hover:border-forest-400 hover:bg-white'
              }`}
            >
              <p className="text-[11px] font-bold uppercase tracking-wider text-charcoal-500">{label}</p>
              <p className={`text-2xl font-extrabold mt-1.5 ${color}`}>{value || 0}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Queue Items Table / List */}
      <section className="surface p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-charcoal-900">{queueLabels[activeQueue]}</h2>
            <p className="text-xs text-charcoal-600 mt-0.5">Records under the selected operational queue.</p>
          </div>
          <span className="text-xs font-bold text-forest-800 px-2.5 py-1 bg-forest-50 border border-forest-200 rounded-lg">
            {filteredQueueItems.length} items shown
          </span>
        </div>
        {filteredQueueItems.length === 0 ? (
          <div className="p-8 text-center bg-ivory-50 border border-ivory-200 rounded-xl">
            <CheckCircle2 className="w-8 h-8 text-forest-700 mx-auto mb-2" />
            <p className="text-sm font-semibold text-charcoal-800">Clear Queue</p>
            <p className="text-xs text-charcoal-500 mt-0.5">Nothing requires immediate attention in this queue category.</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredQueueItems.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 border border-ivory-300 rounded-xl px-4 py-3 bg-white hover:border-sage-400 transition shadow-sm">
                <div>
                  <p className="text-sm font-bold text-charcoal-900">
                    {item.room_number ? `Room ${item.room_number} · ` : ''}{item.title || item.request_type || item.name}
                  </p>
                  <p className="text-xs text-charcoal-600 mt-1">{item.description || item.department || item.unit || 'Operational follow-up required'}</p>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold">
                  {item.priority && (
                    <span className="px-2.5 py-1 rounded bg-brass-50 border border-brass-200 text-brass-800 font-bold">
                      {item.priority}
                    </span>
                  )}
                  {item.status && (
                    <span className="px-2.5 py-1 rounded bg-ivory-200 border border-ivory-300 text-charcoal-800 font-medium">
                      {item.status}
                    </span>
                  )}
                  {item.minutes_overdue > 0 && (
                    <span className="px-2.5 py-1 rounded bg-status-criticalBg border border-red-200 text-status-criticalText font-bold">
                      {item.minutes_overdue} min overdue
                    </span>
                  )}
                  {item.assignee && <span className="text-charcoal-500 font-medium">👤 {item.assignee}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* AI Recommendations Section */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-forest-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-brass-600" />
              Explainable AI Recommendations
            </h2>
            <p className="text-xs text-charcoal-600 mt-0.5">
              Closed-loop decision workflow: Review AI rationales, simulate impact, and approve execution.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-ivory-300 text-charcoal-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-forest-600"
              aria-label="Filter by department"
            >
              <option value="all">All Departments</option>
              {departments.map((department) => (
                <option key={department.id} value={department.name}>{department.name}</option>
              ))}
            </select>
            <button
              onClick={() => setActiveTab('pending')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                activeTab === 'pending'
                  ? 'bg-forest-900 text-white shadow-sm'
                  : 'bg-white text-charcoal-700 border border-ivory-300 hover:bg-ivory-100'
              }`}
            >
              Pending ({pending.length})
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                activeTab === 'all'
                  ? 'bg-forest-900 text-white shadow-sm'
                  : 'bg-white text-charcoal-700 border border-ivory-300 hover:bg-ivory-100'
              }`}
            >
              All History
            </button>
          </div>
        </div>

        {displayRecs.length === 0 ? (
          <div className="surface p-8 text-center bg-white border border-ivory-300 rounded-xl">
            <CheckCircle2 className="w-10 h-10 text-forest-700 mx-auto mb-2" />
            <p className="text-charcoal-900 font-bold text-base">All recommendations have been reviewed</p>
            <p className="text-xs text-charcoal-500 mt-1">The AI engine continuously monitors operations to surface new actionable risks automatically.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {displayRecs.map((rec) => (
              <RecommendationCard
                key={rec.id}
                recommendation={rec}
                onApprove={handleApprove}
                onReject={handleReject}
                onModify={handleModify}
                isProcessing={processing}
              />
            ))}
          </div>
        )}
      </div>

      {/* Room Status & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Room Status */}
        <div className="surface p-5">
          <h3 className="text-sm font-bold text-forest-900 mb-4 flex items-center gap-2">
            <Bed className="w-4 h-4 text-forest-700" />
            Room Status Breakdown
          </h3>
          <div className="space-y-2">
            {Object.entries(data?.room_status_breakdown || {}).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between py-2.5 px-3.5 bg-ivory-50 border border-ivory-200 rounded-lg">
                <span className="text-xs font-semibold text-charcoal-800 capitalize">{status}</span>
                <span className="text-sm font-bold text-forest-900">{count} rooms</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="surface p-5">
          <h3 className="text-sm font-bold text-forest-900 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-forest-700" />
            Recent Activity Audit Log
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {(data?.recent_activity || []).length === 0 ? (
              <p className="text-xs text-charcoal-500 py-4">No recent activity logs found.</p>
            ) : (
              (data?.recent_activity || []).map((log) => (
                <div key={log.id} className="text-xs border-l-2 border-forest-600 pl-3 py-1.5 bg-ivory-50/70 rounded-r">
                  <p className="text-charcoal-900 font-medium">{log.description}</p>
                  <p className="text-charcoal-500 text-[10px] mt-0.5">{formatDateTime(log.created_at)}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* What-If Weather Simulation Modal */}
      <WhatIfSimulationModal
        isOpen={isSimulationModalOpen}
        onClose={() => setIsSimulationModalOpen(false)}
        currentWeather={weatherData}
        onApplySimulation={handleApplySimulation}
        onResetSimulation={handleResetSimulation}
        isSimulationActive={isSimulationActive}
      />
    </div>
  );
};
