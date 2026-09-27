import React, { useState } from 'react';
import {
  Server,
  ChevronDown,
  ChevronUp,
  Cpu,
  Bed,
  Users,
  Calendar,
  AlertTriangle,
  Package,
  CheckCircle,
  Database
} from 'lucide-react';

export const DigitalTwinInspectPanel = ({
  snapshot,
  isSimulation = false
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!snapshot) return null;

  const resortState = snapshot.resort_state || {};
  const staff = snapshot.staff_availability || {};
  const events = snapshot.events || [];
  const operations = snapshot.operational_issues || snapshot.operations || {};
  const inventory = snapshot.inventory_at_risk || snapshot.inventory?.items_at_risk || [];
  const weather = snapshot.weather?.current || {};

  return (
    <div className="surface rounded-xl overflow-hidden shadow-card border border-ivory-300">
      {/* Header Accordion Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 flex items-center justify-between bg-white hover:bg-ivory-50 transition text-left"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-forest-50 border border-forest-200 text-forest-700 shadow-sm">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-charcoal-900">Unified Operational Snapshot (Digital Twin State)</h3>
              {isSimulation && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  SIMULATION ACTIVE
                </span>
              )}
            </div>
            <p className="text-xs text-charcoal-600 mt-0.5">
              Single source of truth data fusion across Resort Telemetry, Staffing, Schedule, and Weather
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold text-forest-800">
          <span>{isOpen ? 'Collapse Telemetry' : 'Inspect Telemetry'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="p-5 border-t border-ivory-300 space-y-6 bg-ivory-50/70 animate-fadeIn">
          {/* Section 1: Resort & Room State */}
          <div>
            <h4 className="text-xs font-bold text-charcoal-800 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Bed className="w-3.5 h-3.5 text-forest-700" />
              Room & Occupancy State
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-white border border-ivory-300 shadow-sm">
                <span className="text-charcoal-500 font-bold uppercase text-[10px]">Occupancy</span>
                <p className="text-xl font-extrabold text-forest-900 mt-1">{resortState.occupancy_pct ?? 0}%</p>
                <span className="text-xs text-charcoal-600 font-medium">
                  {resortState.occupied_rooms}/{resortState.total_rooms} rooms occupied
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-white border border-ivory-300 shadow-sm">
                <span className="text-charcoal-500 font-bold uppercase text-[10px]">Today Check-Ins</span>
                <p className="text-xl font-extrabold text-status-successText mt-1">{resortState.todays_check_ins ?? 0}</p>
                <span className="text-xs text-charcoal-600 font-medium">{resortState.early_arrivals ?? 0} early arrivals</span>
              </div>
              <div className="p-3.5 rounded-xl bg-white border border-ivory-300 shadow-sm">
                <span className="text-charcoal-500 font-bold uppercase text-[10px]">Rooms to Clean</span>
                <p className="text-xl font-extrabold text-brass-700 mt-1">{resortState.rooms_dirty ?? 0}</p>
                <span className="text-xs text-charcoal-600 font-medium">{resortState.rooms_inspecting ?? 0} inspecting</span>
              </div>
              <div className="p-3.5 rounded-xl bg-white border border-ivory-300 shadow-sm">
                <span className="text-charcoal-500 font-bold uppercase text-[10px]">Under Maintenance</span>
                <p className="text-xl font-extrabold text-charcoal-800 mt-1">{resortState.rooms_maintenance ?? 0}</p>
                <span className="text-xs text-charcoal-600 font-medium">Out of service</span>
              </div>
            </div>
          </div>

          {/* Section 2: Department Staffing Availability */}
          <div>
            <h4 className="text-xs font-bold text-charcoal-800 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Users className="w-3.5 h-3.5 text-sage-600" />
              Staff Capacity & Availability by Department
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {Object.entries(staff).map(([dept, details]) => (
                <div key={dept} className="p-3.5 rounded-xl bg-white border border-ivory-300 shadow-sm">
                  <span className="font-bold text-charcoal-900 block truncate text-sm">{dept}</span>
                  <div className="flex items-center justify-between mt-2 text-xs">
                    <span className="text-charcoal-500 font-medium">Available / Sched:</span>
                    <span className="font-extrabold text-forest-900">{details.available} / {details.scheduled ?? details.total ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-xs">
                    <span className="text-charcoal-500 font-medium">Busy on tasks:</span>
                    <span className="font-extrabold text-brass-700">{details.busy}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Scheduled Events & Weather Dependencies */}
          <div>
            <h4 className="text-xs font-bold text-charcoal-800 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Calendar className="w-3.5 h-3.5 text-brass-600" />
              Event Schedule & Weather Vulnerability Matrix
            </h4>
            <div className="space-y-2.5">
              {events.length === 0 ? (
                <p className="text-xs text-charcoal-500">No events currently scheduled.</p>
              ) : (
                events.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-white border border-ivory-300 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-charcoal-900 text-sm">{ev.name}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          ev.outdoor || ev.location_type === 'OUTDOOR'
                            ? 'bg-amber-100 text-amber-900 border border-amber-300'
                            : 'bg-ivory-200 text-charcoal-800 border border-ivory-300'
                        }`}>
                          {ev.outdoor || ev.location_type === 'OUTDOOR' ? 'OUTDOOR' : 'INDOOR'}
                        </span>
                        {ev.weather_dependent && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-forest-50 text-forest-800 border border-forest-200">
                            WEATHER SENSITIVE
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-charcoal-600 mt-1">
                        Location: <span className="font-semibold text-charcoal-800">{ev.location_name || 'Outdoor Pool Deck'}</span> · Expected Guests: <span className="font-semibold text-charcoal-800">{ev.expected_guests ?? 60}</span> · Venue Capacity: <span className="font-semibold text-charcoal-800">{ev.capacity ?? 80}</span>
                      </p>
                    </div>

                    {ev.indoor_alternative && (
                      <div className="text-right">
                        <span className="text-[10px] text-charcoal-500 font-bold block uppercase">Backup Venue:</span>
                        <span className="font-bold text-forest-800 text-xs">{ev.indoor_alternative}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
