import React, { useState, useEffect } from 'react';
import { dashboardAPI, frontDeskAPI } from '../services/api';
import { Building2, Users, Clock, CheckCircle2, AlertCircle, RefreshCw, Bed, ArrowRight } from 'lucide-react';

export const FrontDeskDashboard = () => {
  const [data, setData] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [roomTransitions, setRoomTransitions] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [res, roomsRes, transitionsRes] = await Promise.all([
        dashboardAPI.getFrontDesk(),
        frontDeskAPI.getRooms(),
        frontDeskAPI.getRoomStatusTransitions(),
      ]);
      setData(res.data);
      setRooms(roomsRes.data);
      setRoomTransitions(transitionsRes.data);
    } catch (err) {
      console.error('Failed to fetch:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleBookingAction = async (bookingId, action) => {
    try {
      if (action === 'check-in') {
        await frontDeskAPI.checkIn(bookingId);
      } else {
        await frontDeskAPI.checkOut(bookingId);
      }
      await fetchData();
    } catch (err) {
      alert(`Unable to ${action}: ` + (err.response?.data?.detail || err.message));
    }
  };

  const handleRoomStatus = async (roomId, status) => {
    try {
      await frontDeskAPI.updateRoomStatus(roomId, status);
      await fetchData();
    } catch (err) {
      alert('Unable to update room: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
          <p className="text-sm font-semibold text-charcoal-600">Loading Front Desk Operations...</p>
        </div>
      </div>
    );
  }

  const roomReadiness = data?.room_readiness || {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-charcoal-900">
      {/* Header */}
      <div className="border-b border-ivory-300 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2.5 rounded-xl bg-forest-50 border border-forest-200 text-forest-800 shadow-card">
            <Building2 className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-forest-900">Front Desk Operations</h1>
        </div>
        <p className="text-sm text-charcoal-600">Today's guest arrivals, departures, room keys, and turnover readiness</p>
      </div>

      {/* Room Readiness Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Clean & Ready</p>
          <p className="text-3xl font-extrabold text-status-successText">{roomReadiness.clean || 0}</p>
        </div>
        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Dirty / Turnover</p>
          <p className="text-3xl font-extrabold text-brass-700">{roomReadiness.dirty || 0}</p>
        </div>
        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Inspecting</p>
          <p className="text-3xl font-extrabold text-forest-800">{roomReadiness.inspecting || 0}</p>
        </div>
        <div className="surface p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-charcoal-500 mb-1">Maintenance</p>
          <p className="text-3xl font-extrabold text-status-criticalText">{roomReadiness.maintenance || 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Check-Ins */}
        <div className="surface p-6">
          <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Users className="w-5 h-5 text-status-successText" />
              Today's Check-Ins
            </span>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-forest-50 text-forest-800 border border-forest-200">
              {data?.todays_check_ins?.length || 0} Expected
            </span>
          </h2>
          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            {(data?.todays_check_ins || []).length === 0 ? (
              <p className="text-xs text-charcoal-500 py-4 text-center">No pending check-ins scheduled for today.</p>
            ) : (
              (data?.todays_check_ins || []).map((booking) => (
                <div
                  key={booking.id}
                  className="bg-ivory-50 border border-ivory-300 rounded-xl p-3.5 hover:border-sage-400 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-charcoal-900 text-sm">{booking.guest_name}</p>
                      <p className="text-xs text-charcoal-600 mt-0.5">
                        Room <span className="font-bold text-charcoal-800">{booking.room_number}</span> • {booking.guests_count} guests
                      </p>
                    </div>
                    {booking.early_arrival && (
                      <span className="px-2.5 py-0.5 bg-brass-100 text-brass-900 border border-brass-300 text-[10px] font-bold rounded-md uppercase tracking-wider">
                        EARLY {booking.expected_arrival_time}
                      </span>
                    )}
                  </div>
                  {booking.status === 'confirmed' && (
                    <button
                      onClick={() => handleBookingAction(booking.id, 'check-in')}
                      className="btn-primary mt-3 w-full py-1.5 text-xs font-bold rounded-lg"
                    >
                      Check In Guest
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Today's Check-Outs */}
        <div className="surface p-6">
          <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-brass-700" />
              Today's Check-Outs
            </span>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-ivory-200 text-charcoal-800 border border-ivory-300">
              {data?.todays_check_outs?.length || 0} Expected
            </span>
          </h2>
          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            {(data?.todays_check_outs || []).length === 0 ? (
              <p className="text-xs text-charcoal-500 py-4 text-center">No departures scheduled for today.</p>
            ) : (
              (data?.todays_check_outs || []).map((booking) => (
                <div
                  key={booking.id}
                  className="bg-ivory-50 border border-ivory-300 rounded-xl p-3.5"
                >
                  <p className="font-bold text-charcoal-900 text-sm">{booking.guest_name}</p>
                  <p className="text-xs text-charcoal-600 mt-0.5 font-medium">Room {booking.room_number}</p>
                  {booking.status === 'checked_in' && (
                    <button
                      onClick={() => handleBookingAction(booking.id, 'check-out')}
                      className="mt-3 w-full inline-flex items-center justify-center rounded-lg bg-brass-700 hover:bg-brass-800 text-white px-3 py-1.5 text-xs font-bold transition shadow-sm"
                    >
                      Process Check Out
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Room Status Selector Grid */}
      <div className="surface p-6">
        <h2 className="text-base font-bold text-forest-900 mb-4 flex items-center gap-2">
          <Bed className="w-5 h-5 text-forest-700" />
          Room Housekeeping & Occupancy Status Matrix
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {rooms.map((room) => (
            <div key={room.id} className="bg-ivory-50 border border-ivory-300 rounded-xl p-3 shadow-sm">
              <span className="block text-xs font-bold text-charcoal-900">Room {room.room_number}</span>
              <select
                value={room.status}
                onChange={(event) => handleRoomStatus(room.id, event.target.value)}
                className="mt-2 w-full text-xs font-semibold bg-white border border-ivory-300 rounded-md px-2 py-1 text-charcoal-800 focus:outline-none focus:ring-1 focus:ring-forest-600"
              >
                <option value={room.status}>{room.status.replace('_', ' ')} (current)</option>
                {(roomTransitions[room.status] || []).map((status) => (
                  <option key={status} value={status}>{status.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
