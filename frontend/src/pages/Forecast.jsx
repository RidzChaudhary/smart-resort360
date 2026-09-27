import React, { useState, useEffect } from 'react';
import { forecastAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  Calendar,
  TrendingUp,
  Cpu,
  Bed,
  Users,
  DollarSign,
  AlertCircle,
  RefreshCw,
  CheckCircle2
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

const DepartmentForecastView = ({ data }) => (
  <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-charcoal-900">
    <header className="mb-7">
      <p className="text-xs font-bold uppercase tracking-widest text-forest-700">Department Forecast</p>
      <h1 className="mt-2 text-3xl font-bold text-forest-900">7-Day {data.department.name} Forecast</h1>
      <p className="mt-2 max-w-3xl text-sm text-charcoal-600">{data.method_note}</p>
    </header>

    <section className="mb-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {data.summary_cards.map((card) => (
        <article key={card.label} className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500">{card.label}</p>
          <p className="mt-2 text-2xl font-extrabold text-forest-900">{card.value}</p>
        </article>
      ))}
    </section>

    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-forest-900">Daily Department Outlook</h2>
          <p className="mt-1 text-xs text-charcoal-600">Based on resort occupancy plus recorded departmental workload telemetry.</p>
        </div>
        <span className="text-xs font-bold text-forest-800 px-2.5 py-1 bg-forest-50 border border-forest-200 rounded-lg">{data.days.length} days</span>
      </div>
      <div className="space-y-3">
        {data.days.map((day) => (
          <article key={day.date} className="surface p-5 hover:border-sage-400 transition">
            <h3 className="mb-3 text-sm font-bold text-forest-900">
              {day.day_name} <span className="ml-1 font-medium text-charcoal-500 font-mono text-xs">{day.date}</span>
            </h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 xl:grid-cols-6">
              {data.columns.map((column) => (
                <div key={column.key} className="bg-ivory-50 p-2.5 rounded-lg border border-ivory-200">
                  <dt className="text-[11px] font-bold text-charcoal-500 uppercase">{column.label}</dt>
                  <dd className="mt-1 text-sm font-extrabold text-charcoal-900">{day.metrics[column.key]}{column.key === 'predicted_occupancy_pct' ? '%' : ''}</dd>
                </div>
              ))}
            </dl>
            {day.metrics.items?.length > 0 && (
              <div className="mt-4 border-t border-ivory-200 pt-3">
                <p className="mb-2 text-xs font-bold text-charcoal-800">Projected Item Inventory Levels</p>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {day.metrics.items.filter((item) => item.at_reorder || item.stockout).map((item) => (
                    <div key={item.name} className="flex items-center justify-between gap-2 rounded-lg border border-brass-300 bg-brass-50 px-3 py-2 text-xs">
                      <span className="font-bold text-charcoal-900">{item.name}</span>
                      <span className="shrink-0 font-extrabold text-brass-800">{item.projected_stock} {item.unit}{item.stockout ? ' · Stockout Risk' : ' · Reorder Alert'}</span>
                    </div>
                  ))}
                  {!day.metrics.items.some((item) => item.at_reorder || item.stockout) && (
                    <p className="text-xs text-charcoal-500">No items projected at or below reorder level.</p>
                  )}
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  </main>
);

export const Forecast = () => {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [departmentData, setDepartmentData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const loadForecast = async () => {
      setError('');
      try {
        if (user?.role === 'DEPARTMENT_HEAD') {
          const response = await forecastAPI.getDepartment(7);
          if (active) setDepartmentData(response.data);
        } else {
          const response = await forecastAPI.getOccupancy(7);
          if (active) setData(response.data);
        }
      } catch (requestError) {
        if (active) setError(requestError.response?.data?.detail || 'Failed to fetch forecast.');
      } finally {
        if (active) setLoading(false);
      }
    };
    loadForecast();
    return () => { active = false; };
  }, [user?.role]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
          <p className="text-sm font-semibold text-charcoal-600">Calculating ML Forecast Models...</p>
        </div>
      </div>
    );
  }

  if (user?.role === 'DEPARTMENT_HEAD') {
    if (departmentData) return <DepartmentForecastView data={departmentData} />;
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p role="alert" className="text-sm text-status-criticalText">{error || 'Department forecast is unavailable.'}</p>
        <button type="button" onClick={() => window.location.reload()} className="btn-primary mt-4">Try again</button>
      </div>
    );
  }

  const days = data?.forecast_days || [];
  const summary = data?.overall_summary || {};
  const mlMeta = data?.model_metadata || {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-charcoal-900">
      {/* Header */}
      <div className="border-b border-ivory-300 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2.5 rounded-xl bg-forest-50 border border-forest-200 text-forest-800 shadow-card">
            <Calendar className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-forest-900">7-Day Predictive Operations Forecast</h1>
        </div>
        <p className="text-sm text-charcoal-600">
          Linear Regression where enough booking history exists; otherwise uses the recent observed occupancy average. Staffing uses the current roster, not shift schedules.
        </p>
      </div>

      {/* Summary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Avg 7-Day Occupancy</p>
          <p className="text-3xl font-extrabold text-forest-900">{summary.avg_occupancy_pct}%</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">Peak: {summary.peak_occupancy_pct}% ({summary.peak_occupancy_date})</p>
        </div>

        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Total Expected Arrivals</p>
          <p className="text-3xl font-extrabold text-forest-900">{summary.total_check_ins_7d}</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">{summary.total_check_outs_7d} departures expected</p>
        </div>

        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Projected 7D Revenue</p>
          <p className="text-3xl font-extrabold text-brass-700">${(summary.total_expected_revenue_7d || 0).toLocaleString()}</p>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">Based on confirmed ADR rate models</p>
        </div>

        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Model R²</p>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-forest-700" />
            <p className="text-3xl font-extrabold text-forest-900">
              {mlMeta.model_trained && Number.isFinite(mlMeta.r2_score) ? `${(mlMeta.r2_score * 100).toFixed(1)}%` : 'Insufficient history'}
            </p>
          </div>
          <p className="text-xs text-charcoal-600 mt-1 font-medium">scikit-learn fit on historical bookings</p>
        </div>
      </div>

      {/* Chart 1: Occupancy Curve */}
      <div className="surface p-6">
        <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-forest-700" />
          Occupancy Forecast Trend (% Occupancy)
        </h2>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={days} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="occGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#173F35" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#173F35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e3ddd0" />
              <XAxis dataKey="day_name" stroke="#69716D" tick={{ fill: '#202624', fontSize: 12, fontWeight: 600 }} />
              <YAxis stroke="#69716D" domain={[0, 100]} tick={{ fill: '#202624', fontSize: 12, fontWeight: 600 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e3ddd0', color: '#202624', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
              />
              <Area
                type="monotone"
                dataKey="predicted_occupancy_pct"
                name="Occupancy %"
                stroke="#173F35"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#occGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 2: Housekeeping Cleaning Load & Staffing Gap */}
      <div className="surface p-6">
        <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-sage-600" />
          Housekeeping Turnover Workload vs Roster Capacity
        </h2>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={days} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e3ddd0" />
              <XAxis dataKey="day_name" stroke="#69716D" tick={{ fill: '#202624', fontSize: 12, fontWeight: 600 }} />
              <YAxis stroke="#69716D" tick={{ fill: '#202624', fontSize: 12, fontWeight: 600 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e3ddd0', color: '#202624', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
              />
              <Legend wrapperStyle={{ color: '#202624', fontWeight: 600 }} />
              <Bar dataKey="cleaning_workload_rooms" name="Rooms to Clean" fill="#B08D57" radius={[4, 4, 0, 0]} />
              <Bar dataKey="housekeepers_needed" name="Housekeepers Needed" fill="#173F35" radius={[4, 4, 0, 0]} />
              <Bar dataKey="housekeepers_scheduled" name="Housekeeping Roster" fill="#7A9488" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Day by Day Table */}
      <div className="surface p-6 overflow-x-auto">
        <h2 className="text-base font-bold text-forest-900 mb-4">Detailed Daily Operational Breakdown</h2>
        <table className="w-full text-left text-xs">
          <thead className="bg-ivory-100 text-charcoal-700 uppercase tracking-wider text-[11px] font-bold border-b border-ivory-300">
            <tr>
              <th className="p-3">Date</th>
              <th className="p-3">Day</th>
              <th className="p-3">Occupancy</th>
              <th className="p-3">Arrivals</th>
              <th className="p-3">Departures</th>
              <th className="p-3">Earlies</th>
              <th className="p-3">Cleaning Load</th>
              <th className="p-3">Staff Needed</th>
              <th className="p-3">Roster Gap</th>
              <th className="p-3">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ivory-200">
            {days.map((day) => (
              <tr key={day.date} className="hover:bg-ivory-50 transition">
                <td className="p-3 font-mono text-charcoal-600 font-medium">{day.date}</td>
                <td className="p-3 font-bold text-forest-900">{day.day_name}</td>
                <td className="p-3">
                  <span className="font-extrabold text-forest-900">{day.predicted_occupancy_pct}%</span>
                  <span className="text-[10px] text-charcoal-500 block font-medium">
                    ({day.occupied_rooms}/{day.total_rooms} rooms)
                  </span>
                  {day.overbooking_count > 0 && (
                    <span className="text-[10px] text-brass-700 font-bold block mt-0.5">
                      +{day.overbooking_count} overbookings
                    </span>
                  )}
                </td>
                <td className="p-3 font-bold text-forest-800">{day.check_ins}</td>
                <td className="p-3 font-bold text-charcoal-700">{day.check_outs}</td>
                <td className="p-3 font-bold text-brass-700">{day.early_arrivals}</td>
                <td className="p-3 font-bold text-charcoal-900">{day.cleaning_workload_rooms} rooms</td>
                <td className="p-3 font-semibold text-charcoal-800">{day.housekeepers_needed} staff</td>
                <td className="p-3">
                  {day.staffing_gap > 0 ? (
                    <span className="px-2 py-0.5 bg-status-criticalBg text-status-criticalText border border-red-200 rounded-md font-bold">
                      +{day.staffing_gap} Gap
                    </span>
                  ) : (
                    <span className="text-status-successText font-bold">Balanced ✓</span>
                  )}
                </td>
                <td className="p-3 font-mono font-bold text-forest-700">{(day.ml_confidence_score * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
