import React, { useState, useEffect } from 'react';
import { activityLogAPI } from '../services/api';
import { History, Filter, RefreshCw, Sparkles, CheckCircle2, AlertCircle, UserCheck } from 'lucide-react';
import { formatDateTime } from '../utils/helpers';

export const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchLogs();
  }, [filter]);

  const fetchLogs = async () => {
    try {
      const res = await activityLogAPI.getAll(100, filter === 'all' ? null : filter);
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to fetch activity log:', err);
    } finally {
      setLoading(false);
    }
  };

  const getActionIcon = (actionType) => {
    if (actionType.includes('APPROVED')) return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
    if (actionType.includes('RECOMMENDATION')) return <Sparkles className="w-4 h-4 text-forest-700" />;
    if (actionType.includes('TASK')) return <UserCheck className="w-4 h-4 text-sky-600" />;
    if (actionType.includes('RISK')) return <AlertCircle className="w-4 h-4 text-amber-600" />;
    return <History className="w-4 h-4 text-charcoal-500" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-charcoal-900 flex items-center gap-3">
            <History className="w-7 h-7 text-forest-700" />
            Activity Audit Log
          </h1>
          <p className="text-sm text-charcoal-600 mt-1">
            Comprehensive audit trail of operational decisions, approvals, and task completions
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-charcoal-500" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-1.5 bg-white border border-ivory-300 rounded-lg text-xs font-semibold text-charcoal-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
          >
            <option value="all">All Activity</option>
            <option value="RECOMMENDATION_APPROVED">Recommendations Approved</option>
            <option value="RECOMMENDATION_REJECTED">Recommendations Rejected</option>
            <option value="TASK_ASSIGNED">Tasks Assigned</option>
            <option value="TASK_STATUS_UPDATED">Task Status Changes</option>
            <option value="PO_CREATED">Purchase Orders Created</option>
            <option value="GUEST_REQUEST_SUBMITTED">Guest Requests</option>
          </select>
        </div>
      </div>

      {/* Activity Timeline */}
      <div className="surface p-6 rounded-xl border border-ivory-300 shadow-sm">
        <div className="space-y-4">
          {logs.length === 0 ? (
            <p className="text-sm text-charcoal-500 text-center py-8">No activity logs found for this filter.</p>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="border-l-2 border-ivory-300 pl-4 py-2 hover:border-forest-600 transition bg-ivory-50/50 rounded-r-lg"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{getActionIcon(log.action_type)}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-bold text-forest-800 uppercase tracking-wider">
                        {log.action_type.replace(/_/g, ' ')}
                      </p>
                      <span className="text-xs text-charcoal-500 font-mono">{formatDateTime(log.created_at)}</span>
                    </div>
                    <p className="text-sm text-charcoal-800 leading-relaxed">{log.description}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-charcoal-500">By:</span>
                      <span className="text-xs font-bold text-charcoal-900">{log.user_name}</span>
                      <span className="px-1.5 py-0.5 bg-forest-50 text-forest-800 text-[10px] font-semibold rounded border border-forest-200">
                        {log.user_role}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

