import React, { useState, useEffect } from 'react';
import { dashboardAPI, tasksAPI } from '../services/api';
import { Toast } from '../components/Toast';
import { Users, CheckSquare, User, RefreshCw, AlertCircle, Clock } from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/helpers';

export const DepartmentDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await dashboardAPI.getDepartment();
      setData(res.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (taskId, staffId) => {
    try {
      await tasksAPI.assign(taskId, staffId);
      await fetchData();
      setNotification({ type: 'success', message: 'Task assigned successfully.' });
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to assign: ' + (err.response?.data?.detail || err.message)
      });
    }
  };

  const handleStatusChange = async (taskId, status) => {
    const blockerReason = status === 'BLOCKED'
      ? window.prompt('What is blocking this task?')
      : null;
    if (status === 'BLOCKED' && !blockerReason) return;
    try {
      await tasksAPI.updateStatus(taskId, status, blockerReason);
      await fetchData();
      setNotification({ type: 'success', message: 'Task status updated.' });
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to update task: ' + (err.response?.data?.detail || err.message)
      });
    }
  };

  const nextStatuses = {
    ASSIGNED: ['IN_PROGRESS', 'BLOCKED', 'CANCELLED'],
    IN_PROGRESS: ['BLOCKED', 'COMPLETED', 'CANCELLED'],
    BLOCKED: ['IN_PROGRESS', 'CANCELLED'],
    ESCALATED: ['IN_PROGRESS', 'CANCELLED'],
  };

  const handleEscalate = async (taskId) => {
    const blockerReason = window.prompt('What is blocking this task?');
    if (!blockerReason) return;
    try {
      await tasksAPI.escalate(taskId, blockerReason);
      await fetchData();
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to escalate: ' + (err.response?.data?.detail || err.message)
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
          <p className="text-sm font-semibold text-charcoal-600">Loading Department Operations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-charcoal-900">
      <Toast
        message={notification?.message}
        type={notification?.type}
        onDismiss={() => setNotification(null)}
      />

      {/* Header */}
      <div className="border-b border-ivory-300 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2.5 rounded-xl bg-forest-50 border border-forest-200 text-forest-800 shadow-card">
            <Users className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-forest-900">
            {data?.department?.name} Department Operations
          </h1>
        </div>
        <p className="text-sm text-charcoal-600">Workload distribution, live assignments, and accountability tracking</p>
      </div>

      {/* Task Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Pending</p>
          <p className="text-2xl font-extrabold text-brass-700">{data?.task_summary?.pending || 0}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">In Progress</p>
          <p className="text-2xl font-extrabold text-forest-800">{data?.task_summary?.in_progress || 0}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Completed</p>
          <p className="text-2xl font-extrabold text-status-successText">{data?.task_summary?.completed || 0}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Overdue</p>
          <p className="text-2xl font-extrabold text-status-criticalText">{data?.task_summary?.overdue || 0}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Blocked</p>
          <p className="text-2xl font-extrabold text-status-warningText">{data?.task_summary?.blocked || 0}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Escalated</p>
          <p className="text-2xl font-extrabold text-status-criticalText">{data?.task_summary?.escalated || 0}</p>
        </div>
      </div>

      {/* Tasks List */}
      <div className="surface p-6">
        <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-forest-700" />
            Active Department Tasks
          </span>
          <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-forest-50 text-forest-800 border border-forest-200">
            {data?.tasks?.length || 0} Tasks
          </span>
        </h2>
        <div className="space-y-3">
          {(data?.tasks || []).length === 0 ? (
            <p className="text-xs text-charcoal-500 py-6 text-center">No tasks currently assigned to this department.</p>
          ) : (
            (data?.tasks || []).map((task) => (
              <div key={task.id} className="bg-ivory-50 border border-ivory-300 rounded-xl p-4 shadow-sm hover:border-sage-400 transition">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <div className="flex-1">
                    <h3 className="font-bold text-charcoal-900 text-sm">{task.title}</h3>
                    <p className="text-xs text-charcoal-600 mt-1 leading-relaxed">{task.description}</p>
                    {task.room_number && (
                      <span className="inline-block mt-2 px-2.5 py-0.5 bg-ivory-200 text-charcoal-800 text-xs font-bold rounded-md border border-ivory-300">
                        Room {task.room_number}
                      </span>
                    )}
                    <p className="text-xs text-charcoal-500 mt-2 font-medium">
                      SLA: <span className="text-charcoal-700 font-semibold">{task.sla_minutes ? `${task.sla_minutes} min` : 'Standard'}</span>
                      {task.due_date && ` | Due ${new Date(task.due_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
                    </p>
                    {task.is_overdue && (
                      <p className="text-xs font-bold text-status-criticalText mt-1.5 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Overdue by {task.minutes_overdue} minutes
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

                <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-ivory-300">
                  <span className="text-xs font-bold text-charcoal-700">Assignee:</span>
                  <select
                    value={task.assigned_to || ''}
                    onChange={(e) => e.target.value && handleAssign(task.id, Number(e.target.value))}
                    className="text-xs font-semibold bg-white border border-ivory-300 rounded-lg px-2.5 py-1 text-charcoal-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-forest-600"
                    aria-label={`Assign ${task.title}`}
                  >
                    <option value="">-- Assign Staff --</option>
                    {(data?.team_members || []).map((member) => (
                      <option key={member.id} value={member.id}>{member.name}</option>
                    ))}
                  </select>
                  {nextStatuses[task.status]?.length > 0 && (
                    <select
                      value=""
                      onChange={(e) => e.target.value && handleStatusChange(task.id, e.target.value)}
                      className="text-xs font-semibold bg-white border border-ivory-300 rounded-lg px-2.5 py-1 text-charcoal-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-forest-600"
                      aria-label={`Update status for ${task.title}`}
                    >
                      <option value="">Update Status</option>
                      {nextStatuses[task.status].map((status) => (
                        <option key={status} value={status}>{status.replace('_', ' ')}</option>
                      ))}
                    </select>
                  )}
                  {['BLOCKED', 'IN_PROGRESS'].includes(task.status) && (
                    <button
                      onClick={() => handleEscalate(task.id)}
                      className="ml-auto px-3 py-1 text-xs font-bold text-status-criticalText bg-status-criticalBg border border-red-200 rounded-lg hover:bg-red-100 transition"
                    >
                      Escalate Task
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Team Members */}
      <div className="surface p-6">
        <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-forest-700" />
          Department Team Members ({data?.team_members?.length || 0})
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {(data?.team_members || []).map((member) => (
            <div key={member.id} className="bg-ivory-50 border border-ivory-300 rounded-xl p-3.5 flex items-center gap-3 shadow-sm">
              <div className="w-10 h-10 rounded-full bg-forest-50 border border-forest-200 flex items-center justify-center text-xs font-extrabold text-forest-900">
                {member.name.split(' ').map(n => n[0]).join('')}
              </div>
              <div>
                <p className="text-sm font-bold text-charcoal-900">{member.name}</p>
                <p className="text-xs text-charcoal-500 font-medium">{member.email}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
