import React, { useState, useEffect } from 'react';
import { dashboardAPI, tasksAPI } from '../services/api';
import { CheckSquare, Clock, CheckCircle2, PlayCircle, RefreshCw, AlertCircle } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/helpers';

export const StaffDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await dashboardAPI.getStaff();
      setData(res.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (taskId, newStatus) => {
    try {
      await tasksAPI.updateStatus(taskId, newStatus);
      await fetchData();
    } catch (err) {
      alert('Failed to update status: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleEscalate = async (taskId) => {
    const blockerReason = window.prompt('What is blocking this task?');
    if (!blockerReason) return;
    try {
      await tasksAPI.escalate(taskId, blockerReason);
      await fetchData();
    } catch (err) {
      alert('Failed to escalate: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
          <p className="text-sm font-semibold text-charcoal-600">Loading Assigned Work Orders...</p>
        </div>
      </div>
    );
  }

  const tasks = data?.my_tasks || [];
  const summary = data?.summary || {};

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8 text-charcoal-900">
      {/* Header */}
      <div className="border-b border-ivory-300 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2.5 rounded-xl bg-forest-50 border border-forest-200 text-forest-800 shadow-card">
            <CheckSquare className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-forest-900">My Work Orders & Tasks</h1>
        </div>
        <p className="text-sm text-charcoal-600">Track, execute, and report progress on your assigned tasks</p>
      </div>

      {/* Summary KPI */}
      <div className="grid grid-cols-3 gap-4">
        <div className="surface p-5 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Pending</p>
          <p className="text-3xl font-extrabold text-brass-700">{summary.pending || 0}</p>
        </div>
        <div className="surface p-5 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">In Progress</p>
          <p className="text-3xl font-extrabold text-forest-900">{summary.in_progress || 0}</p>
        </div>
        <div className="surface p-5 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Completed Today</p>
          <p className="text-3xl font-extrabold text-status-successText">{summary.completed_today || 0}</p>
        </div>
      </div>

      {/* Tasks List */}
      <div className="space-y-4">
        {tasks.length === 0 ? (
          <div className="surface p-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-forest-700 mx-auto mb-3" />
            <p className="text-charcoal-900 font-bold text-base">You have no pending tasks right now!</p>
            <p className="text-xs text-charcoal-500 mt-1">New tasks assigned by your department supervisor will appear here.</p>
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className="surface p-5 shadow-card hover:border-sage-400 transition"
            >
              <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                <div className="flex-1">
                  <h3 className="text-base font-bold text-charcoal-900">{task.title}</h3>
                  <p className="text-xs text-charcoal-600 mt-1 leading-relaxed">{task.description}</p>
                  {task.room_number && (
                    <span className="inline-block mt-2 px-2.5 py-0.5 bg-ivory-200 text-charcoal-800 text-xs font-bold rounded-md border border-ivory-300">
                      Room {task.room_number}
                    </span>
                  )}
                  {task.is_overdue && (
                    <p className="text-xs font-bold text-status-criticalText mt-2 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      Overdue by {task.minutes_overdue} min
                    </p>
                  )}
                  {task.blocker_reason && (
                    <p className="text-xs font-semibold text-status-warningText mt-1">Blocked: {task.blocker_reason}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 text-[10px] font-bold rounded border ${getPriorityColor(task.priority)}`}>
                    {task.priority}
                  </span>
                  <span className={`px-2.5 py-0.5 text-[10px] font-bold rounded border ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                </div>
              </div>

              {/* Status Action Buttons */}
              <div className="flex flex-wrap items-center justify-end gap-2 pt-3 border-t border-ivory-300 mt-4">
                {task.status === 'PENDING' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'ASSIGNED')}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-forest-900 hover:bg-forest-800 text-white text-xs font-bold rounded-lg shadow-btn transition"
                  >
                    <PlayCircle className="w-4 h-4 text-brass-300" />
                    <span>Accept Task</span>
                  </button>
                )}

                {task.status === 'ASSIGNED' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'IN_PROGRESS')}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-forest-900 hover:bg-forest-800 text-white text-xs font-bold rounded-lg shadow-btn transition"
                  >
                    <PlayCircle className="w-4 h-4 text-brass-300" />
                    <span>Start Work</span>
                  </button>
                )}

                {task.status === 'IN_PROGRESS' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'COMPLETED')}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-status-success hover:opacity-90 text-white text-xs font-bold rounded-lg shadow-btn transition"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Mark Complete</span>
                  </button>
                )}

                {task.status !== 'COMPLETED' && task.status !== 'ESCALATED' && (
                  <button
                    onClick={() => handleEscalate(task.id)}
                    className="px-3 py-1.5 text-xs font-bold text-status-criticalText bg-status-criticalBg border border-red-200 rounded-lg hover:bg-red-100 transition"
                  >
                    Report Blocker
                  </button>
                )}

                {task.status === 'COMPLETED' && (
                  <span className="text-xs text-status-successText font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" />
                    Completed ✓
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
