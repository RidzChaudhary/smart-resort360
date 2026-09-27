import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Edit3,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Layers
} from 'lucide-react';
import { getPriorityColor, getStatusColor } from '../utils/helpers';

export const RecommendationCard = ({
  recommendation,
  onApprove,
  onReject,
  onModify,
  isProcessing = false
}) => {
  const [showModifyModal, setShowModifyModal] = useState(false);
  const [modifiedQuantity, setModifiedQuantity] = useState(
    recommendation.metrics_data?.staff_needed ||
    recommendation.metrics_data?.reorder_quantity ||
    1
  );
  const [modifyNotes, setModifyNotes] = useState('');

  const isPending = recommendation.status === 'PENDING';

  const handleModifySubmit = (e) => {
    e.preventDefault();
    onModify(recommendation.id, {
      action: 'MODIFY',
      modified_quantity: Number(modifiedQuantity),
      modified_notes: modifyNotes
    });
    setShowModifyModal(false);
  };

  return (
    <div className="surface p-5 relative overflow-hidden group hover:border-sage-400 transition-colors">
      {/* Top Banner & Priority */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-sage-50 text-forest-700 border border-sage-200">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="text-xs font-medium text-charcoal-500 uppercase tracking-wider">
            {recommendation.type} • {recommendation.target_date || 'Upcoming'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded-full border ${getPriorityColor(recommendation.priority)}`}>
            {recommendation.priority} PRIORITY
          </span>
          <span className={`px-2 py-0.5 text-[10px] font-medium rounded border ${getStatusColor(recommendation.status)}`}>
            {recommendation.status}
          </span>
        </div>
      </div>

      {/* Main Title & Action */}
      <h3 className="text-base font-bold text-charcoal-900 mb-2 leading-snug">
        {recommendation.title}
      </h3>

      <div className="bg-sage-50 rounded-lg p-3 border border-sage-200 mb-4">
        <p className="text-xs text-charcoal-500 font-medium uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <ArrowRight className="w-3.5 h-3.5 text-forest-700" />
          Recommended Action
        </p>
        <p className="text-sm font-semibold text-forest-900">
          {recommendation.recommended_action}
        </p>
      </div>

      {/* Explainable AI Rationale */}
      <div className="space-y-3 mb-5 text-xs text-charcoal-600">
        <div>
          <span className="font-semibold text-charcoal-900 mb-1 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-sage-600" />
            Why (Operational Rationale):
          </span>
          <p className="text-charcoal-600 leading-relaxed bg-ivory-100 p-2.5 rounded border border-ivory-300 whitespace-pre-line text-[11px]">
            {recommendation.explanation}
          </p>
        </div>

        <div>
          <span className="font-semibold text-charcoal-900 mb-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-status-successText" />
            Expected Impact:
          </span>
          <p className="text-status-successText leading-relaxed bg-status-successBg p-2 rounded border border-green-200">
            {recommendation.expected_impact}
          </p>
        </div>
      </div>

      {/* All recommendations support the complete manager review flow. */}
      {isPending ? (
        <div className="flex items-center gap-2 pt-3 border-t border-ivory-300">
          <button
            onClick={() => onApprove(recommendation.id)}
            disabled={isProcessing}
            className="btn-primary flex-1 text-xs disabled:opacity-50"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{recommendation.type === 'inventory' ? 'Approve & Create Action' : 'Approve & Execute'}</span>
          </button>

          <button
            onClick={() => setShowModifyModal(true)}
            disabled={isProcessing}
            className="btn-secondary btn-sm"
            title="Modify parameters"
          >
            <Edit3 className="w-3.5 h-3.5 text-sage-600" />
            <span>Modify</span>
          </button>

          <button
            onClick={() => onReject(recommendation.id)}
            disabled={isProcessing}
            className="btn-danger btn-sm"
            title="Decline recommendation"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>Decline</span>
          </button>
        </div>
      ) : (
        <div className="pt-3 border-t border-ivory-300 text-xs text-charcoal-500 flex items-center justify-between">
          <span>Processed by: <strong className="text-charcoal-900">{recommendation.approved_by || 'Manager'}</strong></span>
          <span className="text-[11px] text-status-successText">Closed-Loop Executed</span>
        </div>
      )}

      {/* Modify Modal */}
      {showModifyModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="surface border border-ivory-300 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-charcoal-900 flex items-center gap-2">
              <Edit3 className="w-5 h-5 text-forest-700" />
              Modify Recommendation Parameters
            </h3>
            <p className="text-xs text-charcoal-600">
              Adjust recommended values before approving. The closed-loop engine will create the department action with your modified target.
            </p>

            <form onSubmit={handleModifySubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">
                  {recommendation.type === 'staffing' ? 'Adjust Staff Count (Shifts)' : 'Adjust Order Quantity'}
                </label>
                <input
                  type="number"
                  step="any"
                  min="1"
                  required
                  value={modifiedQuantity}
                  onChange={(e) => setModifiedQuantity(e.target.value)}
                  className="w-full bg-white border border-ivory-300 rounded-lg px-3 py-2 text-charcoal-900 text-sm focus:outline-none focus:ring-2 focus:ring-forest-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">
                  Manager Adjustment Reason / Notes
                </label>
                <textarea
                  rows={3}
                  value={modifyNotes}
                  onChange={(e) => setModifyNotes(e.target.value)}
                  placeholder="e.g. VIP group arriving early, adding 1 extra shift buffer..."
                  className="w-full bg-white border border-ivory-300 rounded-lg px-3 py-2 text-charcoal-900 text-sm placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-ivory-200">
                <button
                  type="button"
                  onClick={() => setShowModifyModal(false)}
                  className="px-4 py-2 bg-white border border-ivory-300 hover:bg-ivory-50 text-charcoal-700 rounded-lg text-xs font-semibold shadow-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-forest-800 hover:bg-forest-900 text-white rounded-lg text-xs font-bold shadow-sm transition"
                >
                  Confirm & Execute Modified Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

