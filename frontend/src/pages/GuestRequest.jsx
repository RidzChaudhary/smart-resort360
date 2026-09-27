import React, { useState } from 'react';
import { guestRequestsAPI } from '../services/api';
import { QrCode, Send, CheckCircle2, AlertCircle } from 'lucide-react';

export const GuestRequest = () => {
  const [formData, setFormData] = useState({
    room_number: '',
    guest_name: '',
    request_type: 'AC/Maintenance',
    description: '',
    priority: 'MEDIUM'
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const requestTypes = [
    'AC/Maintenance',
    'Housekeeping/Towels',
    'F&B/Room Service',
    'Amenities',
    'Luggage',
    'Other'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
  
    try {
      await guestRequestsAPI.create(formData);
      setSubmitted(true);
      setLoading(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit request');
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      room_number: '',
      guest_name: '',
      request_type: 'AC/Maintenance',
      description: '',
      priority: 'MEDIUM'
    });
    setSubmitted(false);
    setError('');
  };

  if (submitted) {
    return (
      <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4">
        <div className="max-w-md w-full surface border border-ivory-300 rounded-2xl p-8 text-center shadow-lg">
          <div className="w-16 h-16 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-emerald-700" />
          </div>
          <h2 className="text-2xl font-bold text-charcoal-900 mb-2">Request Submitted Successfully!</h2>
          <p className="text-sm text-charcoal-600 mb-6">
            Your request has been routed to the appropriate department. Our team will respond shortly.
          </p>
          <button
            onClick={handleReset}
            className="px-6 py-2.5 bg-forest-800 hover:bg-forest-900 text-white font-semibold rounded-lg shadow-sm transition"
          >
            Submit Another Request
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-8">
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-forest-900 mb-4 shadow-sm">
            <QrCode className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-charcoal-900 mb-2">Guest Service Request</h1>
          <p className="text-sm text-charcoal-600">
            Submit operational requests requiring staff attention or coordination
          </p>
        </div>

        {/* Form */}
        <div className="surface border border-ivory-300 rounded-2xl p-8 shadow-sm">
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2">
                  Room Number *
                </label>
                <input
                  type="text"
                  required
                  value={formData.room_number}
                  onChange={(e) => setFormData({ ...formData, room_number: e.target.value })}
                  placeholder="e.g., 301"
                  className="w-full bg-white border border-ivory-300 rounded-lg px-4 py-2.5 text-charcoal-900 text-sm placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2">
                  Guest Name (Optional)
                </label>
                <input
                  type="text"
                  value={formData.guest_name}
                  onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                  placeholder="Your name"
                  className="w-full bg-white border border-ivory-300 rounded-lg px-4 py-2.5 text-charcoal-900 text-sm placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2">
                Request Type *
              </label>
              <select
                required
                value={formData.request_type}
                onChange={(e) => setFormData({ ...formData, request_type: e.target.value })}
                className="w-full bg-white border border-ivory-300 rounded-lg px-4 py-2.5 text-charcoal-900 text-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
              >
                {requestTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2">
                Request Description *
              </label>
              <textarea
                required
                rows={4}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Please describe your request in detail. For maintenance issues, include symptoms and location."
                className="w-full bg-white border border-ivory-300 rounded-lg px-4 py-2.5 text-charcoal-900 text-sm placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500 resize-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-2">
                Urgency Level
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['LOW', 'MEDIUM', 'HIGH'].map((priority) => (
                  <button
                    key={priority}
                    type="button"
                    onClick={() => setFormData({ ...formData, priority })}
                    className={`py-2 px-4 rounded-lg text-xs font-bold uppercase tracking-wider transition ${
                      formData.priority === priority
                        ? 'bg-forest-800 text-white shadow-sm'
                        : 'bg-white text-charcoal-700 hover:bg-ivory-50 border border-ivory-300'
                    }`}
                  >
                    {priority}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-forest-800 hover:bg-forest-900 text-white font-bold rounded-lg shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Send className="w-5 h-5" />
              <span>{loading ? 'Submitting...' : 'Submit Service Request'}</span>
            </button>

            <p className="text-xs text-charcoal-500 text-center mt-4">
              Your request will be routed to the appropriate department and tracked operationally.
            </p>
          </form>
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-charcoal-500">
            For simple requests like extra towels, you may also ask staff directly without submitting a form.
          </p>
        </div>
      </div>
    </div>
  );
};

