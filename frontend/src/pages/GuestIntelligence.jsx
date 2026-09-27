import React, { useEffect, useState, useCallback } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Flame,
  MessageSquare,
  Plus,
  RefreshCw,
  Sparkles,
  Star,
  Target,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import { guestIntelligenceAPI } from '../services/api';

/* ───────────────────────────────────────────────────────────────
   Palette helpers
─────────────────────────────────────────────────────────────── */
const SEGMENT_PALETTE = {
  WELLNESS:  { bg: 'bg-forest-50',  border: 'border-forest-200',  badge: 'bg-forest-100 text-forest-900',  bar: 'bg-forest-500',  dot: 'bg-forest-500'  },
  FAMILY:    { bg: 'bg-brass-50',   border: 'border-brass-200',   badge: 'bg-brass-100 text-brass-900',    bar: 'bg-brass-500',   dot: 'bg-brass-500'   },
  ROMANTIC:  { bg: 'bg-red-100',    border: 'border-red-200',     badge: 'bg-red-200 text-red-600',        bar: 'bg-red-500',     dot: 'bg-red-500'     },
  ADVENTURE: { bg: 'bg-sage-50',    border: 'border-sage-200',    badge: 'bg-sage-100 text-sage-700',      bar: 'bg-sage-500',    dot: 'bg-sage-500'    },
  FOOD:      { bg: 'bg-brass-50',   border: 'border-brass-300',   badge: 'bg-brass-200 text-brass-800',    bar: 'bg-brass-400',   dot: 'bg-brass-400'   },
  LUXURY:    { bg: 'bg-charcoal-50',border: 'border-charcoal-200',badge: 'bg-charcoal-100 text-charcoal-800', bar: 'bg-charcoal-500', dot: 'bg-charcoal-500' },
};
const defaultPalette = { bg: 'bg-sage-50', border: 'border-sage-200', badge: 'bg-sage-100 text-forest-800', bar: 'bg-forest-500', dot: 'bg-forest-500' };
const getPalette = (name) => SEGMENT_PALETTE[name?.toUpperCase()] || defaultPalette;

const SENTIMENT_CONFIG = {
  POSITIVE: { color: 'text-forest-700', bg: 'bg-forest-50',   bar: 'bg-forest-500', icon: ThumbsUp },
  MIXED:    { color: 'text-brass-700',  bg: 'bg-brass-50',    bar: 'bg-brass-500',  icon: MessageSquare },
  NEUTRAL:  { color: 'text-charcoal-600', bg: 'bg-charcoal-50', bar: 'bg-charcoal-400', icon: MessageSquare },
  NEGATIVE: { color: 'text-red-600',   bg: 'bg-red-100',     bar: 'bg-red-500',    icon: ThumbsDown },
};

/* ───────────────────────────────────────────────────────────────
   Sub-components
─────────────────────────────────────────────────────────────── */

function StatCard({ label, value, sub, icon: Icon, accent = 'text-forest-700', highlight }) {
  return (
    <div className="bg-white border border-ivory-300 rounded-xl p-5 shadow-sm">
      <p className="text-xs font-medium text-charcoal-500 uppercase tracking-wider">{label}</p>
      <p className={`mt-1.5 text-3xl font-bold font-mono ${highlight || 'text-charcoal-900'}`}>
        {value ?? '—'}
      </p>
      {sub && <p className="mt-1 text-xs text-charcoal-400">{sub}</p>}
    </div>
  );
}

function SegmentCard({ segment }) {
  const [expanded, setExpanded] = useState(false);
  const palette = getPalette(segment.name);
  const sat = segment.avg_satisfaction;

  return (
    <div className={`rounded-xl border ${palette.border} ${palette.bg} overflow-hidden`}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-3 hover:opacity-90 transition"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${palette.badge}`}>
            {segment.name}
          </span>
          <span className="text-sm font-medium text-charcoal-700 shrink-0">
            {segment.guest_count} {segment.guest_count === 1 ? 'guest' : 'guests'}
          </span>
          {sat != null && (
            <span className="flex items-center gap-1 text-sm font-semibold text-charcoal-800">
              <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
              Avg {sat.toFixed(2)}/5.0
            </span>
          )}
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-charcoal-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-charcoal-500 shrink-0" />}
      </button>

      {expanded && (
        <div className="border-t border-white/60 px-5 py-4 space-y-3">
          {segment.top_activities?.length ? (
            <>
              <p className="text-[11px] font-bold text-charcoal-500 uppercase tracking-wider">Top Activities</p>
              <div className="space-y-2">
                {segment.top_activities.map((act) => (
                  <div key={act.id} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`shrink-0 w-2 h-2 rounded-full ${palette.dot}`} />
                      <span className="text-sm text-charcoal-800 font-medium truncate">{act.name}</span>
                      <span className="text-xs text-charcoal-400 shrink-0">({act.count} bookings)</span>
                    </div>
                    {act.avg_rating != null && (
                      <span className="flex items-center gap-0.5 text-xs font-semibold text-amber-600 shrink-0">
                        <Star className="w-3 h-3 fill-amber-400" />
                        {act.avg_rating}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-charcoal-400">No activity interactions recorded yet for this segment.</p>
          )}
        </div>
      )}
    </div>
  );
}

function SentimentBar({ counts }) {
  const total = Object.values(counts).reduce((s, v) => s + v, 0);
  if (total === 0) return <p className="text-sm text-charcoal-400 mt-4">No feedback recorded yet.</p>;

  const order = ['POSITIVE', 'MIXED', 'NEUTRAL', 'NEGATIVE'];

  return (
    <div className="mt-4 space-y-3">
      {order.filter((k) => counts[k]).map((key) => {
        const cfg = SENTIMENT_CONFIG[key] || SENTIMENT_CONFIG.NEUTRAL;
        const Icon = cfg.icon;
        const pct = Math.round((counts[key] / total) * 100);
        return (
          <div key={key}>
            <div className="flex items-center justify-between mb-1">
              <span className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${cfg.color}`}>
                <Icon className="w-3.5 h-3.5" />
                {key}
              </span>
              <span className="text-xs font-bold text-charcoal-700">{counts[key]}</span>
            </div>
            <div className="h-2 bg-ivory-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TopicPills({ topics, label }) {
  if (!topics?.length) return null;
  return (
    <div className="mt-4">
      <p className="text-[11px] font-bold text-charcoal-400 uppercase tracking-wider mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {topics.map((t) => (
          <span key={t.topic} className="inline-flex items-center gap-1.5 rounded-lg border border-ivory-300 bg-ivory-50 px-2.5 py-1 text-xs font-semibold text-charcoal-700">
            <span>{t.topic.replaceAll('_', ' ')}</span>
            <span className="ml-1 font-bold text-charcoal-400">×{t.count}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function RecommendationPerformancePanel({ perf }) {
  if (!perf) return null;
  const topRecs = perf.top_recommended_activities || [];
  const maxCount = Math.max(1, ...topRecs.map((r) => r.count));

  return (
    <section className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <Target className="w-5 h-5 text-forest-700" />
        <h2 className="text-base font-bold text-charcoal-900">Recommendation Engine Performance</h2>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Generated', value: perf.total_generated },
          { label: 'Acceptance Rate', value: `${perf.acceptance_rate}%`, highlight: perf.acceptance_rate > 30 ? 'text-emerald-600' : 'text-charcoal-900' },
          { label: 'Completion Rate', value: `${perf.completion_rate}%`, highlight: perf.completion_rate > 50 ? 'text-emerald-600' : 'text-charcoal-900' },
          {
            label: 'Status',
            value: null,
            custom: (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {Object.entries(perf.status_breakdown || {}).slice(0, 3).map(([k, v]) => (
                  <span key={k} className="text-xs font-semibold text-charcoal-600 bg-ivory-100 border border-ivory-300 rounded px-2 py-0.5">
                    {k}: {v}
                  </span>
                ))}
              </div>
            ),
          },
        ].map((item) => (
          <div key={item.label} className="bg-ivory-50 border border-ivory-200 rounded-lg p-3">
            <p className="text-xs text-charcoal-500 uppercase tracking-wide font-medium">{item.label}</p>
            {item.custom || (
              <p className={`mt-1 text-2xl font-bold font-mono ${item.highlight || 'text-charcoal-900'}`}>{item.value}</p>
            )}
          </div>
        ))}
      </div>

      {topRecs.length > 0 && (
        <>
          <p className="text-xs font-bold text-charcoal-500 uppercase tracking-wider mb-3">Top Recommended Activities</p>
          <div className="space-y-2.5">
            {topRecs.map((rec) => (
              <div key={rec.name} className="flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-charcoal-800 truncate">{rec.name}</span>
                    <span className="text-xs font-bold text-charcoal-500 shrink-0 ml-2">{rec.count} recs</span>
                  </div>
                  <div className="h-1.5 bg-ivory-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-forest-500 rounded-full transition-all"
                      style={{ width: `${(rec.count / maxCount) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

/* Add Activity Form */
const initialForm = {
  name: '', description: '', category: '', tags: '', capacity: 12, crowd_level: 'MODERATE',
};

function AddActivityForm({ onAdded }) {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await guestIntelligenceAPI.createActivity({
        ...form,
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
        capacity: Number(form.capacity),
        available_slots: Number(form.capacity),
      });
      setForm(initialForm);
      setOpen(false);
      onAdded?.();
    } catch (err) {
      setError(err.response?.data?.detail || 'Activity could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-forest-800 hover:bg-forest-900 text-white text-sm font-semibold rounded-lg shadow-sm transition"
      >
        <Plus className="w-4 h-4" /> Add Activity
      </button>
    );
  }

  return (
    <div className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
      <h3 className="text-base font-bold text-charcoal-900 mb-4">Add Resort Activity</h3>
      {error && <p className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-2.5">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-3">
        <input required minLength={2} maxLength={160} value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Activity name"
          className="w-full rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500" />
        <textarea required minLength={5} maxLength={2000} value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="What guests can expect" rows={2}
          className="w-full rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500 resize-none" />
        <div className="grid grid-cols-2 gap-3">
          <input required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
            placeholder="Category (e.g. Wellness)"
            className="rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500" />
          <input required type="number" min={1} max={10000} value={form.capacity}
            onChange={(e) => setForm({ ...form, capacity: e.target.value })} aria-label="Capacity"
            className="rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500" />
        </div>
        <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })}
          placeholder="Tags: relaxation, family-friendly, wellness"
          className="w-full rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500" />
        <div className="flex items-center gap-3">
          <select value={form.crowd_level} onChange={(e) => setForm({ ...form, crowd_level: e.target.value })}
            className="flex-1 rounded-lg border border-ivory-300 bg-white px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500">
            <option value="LOW">Low crowd</option>
            <option value="MODERATE">Moderate crowd</option>
            <option value="HIGH">High crowd</option>
          </select>
          <button disabled={saving}
            className="px-5 py-2 bg-forest-800 hover:bg-forest-900 text-white font-bold rounded-lg shadow-sm transition flex items-center gap-1.5 disabled:opacity-50">
            <Plus className="w-4 h-4" />{saving ? 'Saving…' : 'Add'}
          </button>
          <button type="button" onClick={() => setOpen(false)}
            className="px-4 py-2 border border-ivory-300 bg-white text-charcoal-700 font-medium rounded-lg hover:bg-ivory-50 transition text-sm">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

/* Activity Catalog */
function ActivityCatalog({ activities, onUpdate }) {
  const handleToggle = async (activity) => {
    try {
      await guestIntelligenceAPI.updateActivity(activity.id, { active: !activity.active });
      onUpdate?.();
    } catch {
      // ignore
    }
  };

  const handleSlotBlur = async (activity, value) => {
    const num = Number(value);
    if (num !== activity.available_slots && num <= activity.capacity) {
      try {
        await guestIntelligenceAPI.updateActivity(activity.id, { available_slots: num });
        onUpdate?.();
      } catch {
        // ignore
      }
    }
  };

  const handleCrowd = async (activity, crowd_level) => {
    try {
      await guestIntelligenceAPI.updateActivity(activity.id, { crowd_level });
      onUpdate?.();
    } catch {
      // ignore
    }
  };

  return (
    <section className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <Zap className="w-5 h-5 text-forest-700" />
        <h2 className="text-base font-bold text-charcoal-900">Activity Catalog</h2>
      </div>
      <p className="text-xs text-charcoal-500 mb-4">Availability and crowd level are manager-controlled. Not live telemetry.</p>
      {activities.length === 0 ? (
        <p className="text-sm text-charcoal-400">No resort activities configured.</p>
      ) : (
        <div className="space-y-3">
          {activities.map((activity) => (
            <div key={activity.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-ivory-200 pb-3 last:border-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-charcoal-900 truncate">{activity.name}</p>
                  {activity.is_training_sample && (
                    <span className="shrink-0 text-[9px] uppercase font-bold text-amber-800 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">Demo</span>
                  )}
                  {!activity.active && (
                    <span className="shrink-0 text-[9px] uppercase font-bold text-slate-500 bg-slate-50 border border-slate-200 rounded px-1.5 py-0.5">Paused</span>
                  )}
                </div>
                <p className="text-xs text-charcoal-400 mt-0.5">{activity.category} · capacity {activity.capacity}</p>
              </div>
              <label className="text-xs font-semibold text-charcoal-600 shrink-0">
                Available:
                <input type="number" min={0} max={activity.capacity} defaultValue={activity.available_slots}
                  onBlur={(e) => handleSlotBlur(activity, e.target.value)}
                  className="ml-2 w-14 rounded border border-ivory-300 bg-white px-2 py-1 text-xs font-bold text-charcoal-900"
                  aria-label={`Available for ${activity.name}`} />
              </label>
              <select value={activity.crowd_level} onChange={(e) => handleCrowd(activity, e.target.value)}
                className="rounded border border-ivory-300 bg-white px-2 py-1 text-xs font-semibold text-charcoal-800">
                <option value="LOW">Low</option>
                <option value="MODERATE">Moderate</option>
                <option value="HIGH">High</option>
              </select>
              <button type="button" onClick={() => handleToggle(activity)}
                className={`shrink-0 px-2.5 py-1 border rounded text-xs font-semibold shadow-sm transition ${
                  activity.active ? 'border-ivory-300 bg-white text-charcoal-800 hover:bg-ivory-50' : 'border-forest-700 bg-forest-800 text-white hover:bg-forest-900'
                }`}>
                {activity.active ? 'Pause' : 'Activate'}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/* ───────────────────────────────────────────────────────────────
   Main Page
─────────────────────────────────────────────────────────────── */
export const GuestIntelligence = () => {
  const [overview, setOverview] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ovRes, acRes] = await Promise.all([
        guestIntelligenceAPI.getManagerOverview(),
        guestIntelligenceAPI.getManagerActivities(),
      ]);
      setOverview(ovRes.data);
      setActivities(acRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Guest intelligence could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-forest-700" />
      </div>
    );
  }

  const trainingSamples = overview?.training_data || {};
  const hasTraining = Object.values(trainingSamples).some(Boolean);
  const behavioralSegments = overview?.behavioral_segments || [];
  const sentimentCounts = overview?.feedback?.sentiment_counts || {};
  const allTopics = overview?.feedback?.all_topics || [];
  const trainingTopics = overview?.feedback?.training_topics || [];

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* ── Page Header ──────────────────────────────────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-forest-700">Manager Analytics</p>
          <h1 className="mt-1 text-2xl md:text-3xl font-bold text-charcoal-900 flex items-center gap-3">
            <Brain className="w-7 h-7 text-forest-700" />
            Guest Intelligence
          </h1>
          <p className="mt-1 text-sm text-charcoal-500">
            Stay patterns, experience engagement, behavioral segments, and recurring feedback themes.
          </p>
        </div>
        <button type="button" onClick={loadData}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-ivory-300 rounded-lg text-xs font-semibold text-charcoal-800 hover:bg-ivory-50 shadow-sm transition">
          <RefreshCw className="w-4 h-4 text-forest-700" /> Refresh
        </button>
      </header>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 font-medium">{error}</div>
      )}

      {/* ── Training Data Banner ─────────────────────────────────── */}
      {hasTraining && (
        <aside className="border border-amber-200 bg-amber-50 p-3.5 rounded-xl shadow-sm">
          <p className="text-xs font-bold text-amber-900 uppercase tracking-wider">Synthetic training samples — excluded from live analytics</p>
          <p className="mt-1 text-xs text-amber-800 font-medium">
            {trainingSamples.profiles || 0} profiles · {trainingSamples.activities || 0} activities · {trainingSamples.interactions || 0} interactions · {trainingSamples.feedback || 0} feedback · {trainingSamples.requests || 0} requests
          </p>
        </aside>
      )}

      {/* ── KPI Stat Cards ───────────────────────────────────────── */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Guest Profiles"
          value={overview?.guest_count ?? 0}
          sub="Pseudonymised — no PII stored"
          icon={Users}
        />
        <StatCard
          label="Activity Interactions"
          value={overview?.total_activity_interactions ?? 0}
          sub="Views, bookings, completions"
          icon={BarChart3}
        />
        <StatCard
          label="Avg Satisfaction"
          value={overview?.avg_satisfaction != null ? `${overview.avg_satisfaction.toFixed(2)}/5.0` : '—'}
          sub="From guest ratings"
          icon={Star}
          highlight={overview?.avg_satisfaction >= 4 ? 'text-emerald-600' : overview?.avg_satisfaction >= 3 ? 'text-amber-600' : 'text-charcoal-900'}
        />
        <StatCard
          label="Feedback (7d)"
          value={overview?.feedback_7d_count ?? 0}
          sub="Last 7 days"
          icon={MessageSquare}
        />
      </section>

      {/* ── Two-column: Behavioral Segments + Sentiment ──────────── */}
      <div className="grid gap-6 lg:grid-cols-2">

        {/* Behavioral Segments */}
        <section className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-forest-700" />
            <h2 className="text-base font-bold text-charcoal-900">Behavioral Segments</h2>
          </div>
          <p className="text-xs text-charcoal-400 mb-4">
            KMeans clustering on stay patterns, party size, and activity interactions. Labels derived from behavioral signals.
          </p>
          {behavioralSegments.length ? (
            <div className="space-y-3">
              {behavioralSegments.map((seg) => (
                <SegmentCard key={seg.name} segment={seg} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-charcoal-400">Segments appear as guests verify stays and interact with activities.</p>
          )}
        </section>

        {/* Sentiment Analysis */}
        <section className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-forest-700" />
            <h2 className="text-base font-bold text-charcoal-900">Sentiment Analysis (30d)</h2>
          </div>
          <p className="text-xs text-charcoal-400 mb-1">
            Keyword-based sentiment from guest feedback comments. No guest identities shown.
          </p>

          <SentimentBar counts={sentimentCounts} />

          {allTopics.length > 0 && <TopicPills topics={allTopics} label="Top Topics (all feedback)" />}

          {trainingTopics.length > 0 && (
            <div className="mt-5 border-t border-ivory-200 pt-4">
              <p className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-2">Demo Training Themes · not live issues</p>
              <div className="flex flex-wrap gap-1.5">
                {trainingTopics.map((t) => (
                  <span key={t.topic} className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                    {t.topic.replaceAll('_', ' ')} · {t.count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* ── Recommendation Engine Performance ────────────────────── */}
      <RecommendationPerformancePanel perf={overview?.recommendation_performance} />

      {/* ── Activity Catalog + Add Activity ──────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ActivityCatalog activities={activities} onUpdate={loadData} />
        <div className="space-y-4">
          <AddActivityForm onAdded={loadData} />
          {/* Activity Trend Sparkline */}
          {(overview?.activity_trends?.length > 0 || overview?.training_activity_trends?.length > 0) && (
            <section className="bg-white border border-ivory-300 rounded-xl shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Flame className="w-4 h-4 text-forest-700" />
                <h2 className="text-sm font-bold text-charcoal-900">Activity Trends · 14 days</h2>
              </div>
              <ActivityTrendBars
                trends={overview.activity_trends || []}
                trainingTrends={overview.training_activity_trends || []}
              />
            </section>
          )}
        </div>
      </div>
    </main>
  );
};

/* Activity Trend mini-chart */
function ActivityTrendBars({ trends, trainingTrends }) {
  const trendDays = trends.length ? trends : trainingTrends;
  const trainingMap = new Map(trainingTrends.map((d) => [d.date, d]));
  const keys = [...new Set([...trends, ...trainingTrends].flatMap((d) => Object.keys(d).filter((k) => k !== 'date')))];
  const maxVal = Math.max(1, ...trendDays.map((d) => keys.reduce((s, k) => s + (d[k] || 0) + (trainingMap.get(d.date)?.[k] || 0), 0)));

  if (!trendDays.length) {
    return <p className="text-sm text-charcoal-400">No activity interactions recorded yet.</p>;
  }

  return (
    <>
      <div className="flex h-28 items-end gap-1 border-b border-ivory-200 pb-2">
        {trendDays.map((day) => {
          const tDay = trainingMap.get(day.date) || {};
          const real = keys.reduce((s, k) => s + (day[k] || 0), 0);
          const training = keys.reduce((s, k) => s + (tDay[k] || 0), 0);
          return (
            <div key={day.date} className="flex h-full flex-1 min-w-0 flex-col justify-end"
              title={`${day.date}: ${real} guest, ${training} training`}>
              <div className="w-full rounded-t-sm bg-amber-300" style={{ height: `${(training / maxVal) * 100}%` }} />
              <div className="w-full bg-forest-600" style={{ height: `${(real / maxVal) * 100}%` }} />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-charcoal-500 font-medium">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 bg-forest-600 rounded-sm" />Guest</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 bg-amber-300 rounded-sm" />Training</span>
      </div>
    </>
  );
}
