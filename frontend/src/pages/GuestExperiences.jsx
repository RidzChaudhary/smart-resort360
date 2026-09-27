import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, Check, ClipboardList, LogIn, MapPin, MessageSquareText, QrCode, Sparkles, Star } from 'lucide-react';
import { guestIntelligenceAPI } from '../services/api';

const loadGuestView = async (guestToken) => {
  const [profileResponse, recommendationResponse, activityResponse, requestResponse] = await Promise.all([
    guestIntelligenceAPI.getProfile(guestToken),
    guestIntelligenceAPI.getRecommendations(guestToken, 5),
    guestIntelligenceAPI.getActivities(guestToken),
    guestIntelligenceAPI.getMyRequests(guestToken),
  ]);
  return {
    profile: profileResponse.data,
    recommendations: recommendationResponse.data,
    activities: activityResponse.data,
    requests: requestResponse.data,
  };
};

export const GuestExperiences = () => {
  const [roomNumber, setRoomNumber] = useState('');
  const [guestName, setGuestName] = useState('');
  const [email, setEmail] = useState('guest.demo@resort360.com');
  const [password, setPassword] = useState('guest123');
  const [loginMode, setLoginMode] = useState('account');
  const [token, setToken] = useState(() => sessionStorage.getItem('guestToken') || '');
  const [guest, setGuest] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('guestAccount') || 'null');
    } catch {
      return null;
    }
  });
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [activities, setActivities] = useState([]);
  const [requests, setRequests] = useState([]);
  const [activeTab, setActiveTab] = useState('recommended');
  const [feedback, setFeedback] = useState('');
  const [requestForm, setRequestForm] = useState({ request_type: 'Housekeeping/Towels', description: '', priority: 'MEDIUM' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(() => Boolean(sessionStorage.getItem('guestToken')));
  const [workingId, setWorkingId] = useState(null);

  useEffect(() => {
    if (!token) return;
    let isCurrentSession = true;
    loadGuestView(token).then((view) => {
      if (!isCurrentSession) return;
      setProfile(view.profile);
      setRecommendations(view.recommendations);
      setActivities(view.activities);
      setRequests(view.requests);
      setLoading(false);
    }).catch((requestError) => {
      if (!isCurrentSession) return;
      setError(requestError.response?.data?.detail || 'Guest session could not be restored.');
      sessionStorage.removeItem('guestToken');
      sessionStorage.removeItem('guestAccount');
      window.dispatchEvent(new Event('guest-session-changed'));
      setToken('');
      setGuest(null);
      setLoading(false);
    });
    return () => { isCurrentSession = false; };
  }, [token]);

  const handleGuestLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const response = await guestIntelligenceAPI.login(email, password);
      setToken(response.data.access_token);
      setGuest(response.data.guest);
      sessionStorage.setItem('guestToken', response.data.access_token);
      sessionStorage.setItem('guestAccount', JSON.stringify(response.data.guest));
      window.dispatchEvent(new Event('guest-session-changed'));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Guest login failed.');
      setLoading(false);
    }
  };

  const handleSession = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const response = await guestIntelligenceAPI.createSession(roomNumber, guestName);
      setToken(response.data.access_token);
      setGuest(response.data.guest);
      sessionStorage.setItem('guestToken', response.data.access_token);
      sessionStorage.setItem('guestAccount', JSON.stringify(response.data.guest));
      window.dispatchEvent(new Event('guest-session-changed'));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Stay verification failed.');
      setLoading(false);
    }
  };

  const recordInteraction = async (activityId, interactionType, rating = null) => {
    setWorkingId(activityId);
    setError('');
    setMessage('');
    try {
      await guestIntelligenceAPI.recordInteraction(token, {
        activity_id: activityId,
        interaction_type: interactionType,
        ...(rating ? { rating } : {}),
      });
      const view = await loadGuestView(token);
      setProfile(view.profile);
      setRecommendations(view.recommendations);
      setActivities(view.activities);
      setRequests(view.requests);
      setMessage(interactionType === 'BOOKED' ? 'Your place is reserved.' : 'Your experience has been updated.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update this activity.');
    } finally {
      setWorkingId(null);
    }
  };

  const submitFeedback = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const response = await guestIntelligenceAPI.submitFeedback(token, { comment: feedback });
      setFeedback('');
      setMessage(`Thanks for sharing. Your feedback was noted as ${response.data.sentiment.toLowerCase()}.`);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Feedback could not be submitted.');
    }
  };

  const submitRequest = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      await guestIntelligenceAPI.createMyRequest(token, requestForm);
      setRequestForm({ ...requestForm, description: '' });
      const view = await loadGuestView(token);
      setProfile(view.profile);
      setRecommendations(view.recommendations);
      setActivities(view.activities);
      setRequests(view.requests);
      setMessage('Your service request has been sent to the resort team.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Your request could not be submitted.');
    }
  };

  const currentState = new Map(activities.map((activity) => [activity.id, activity.interaction_status]));
  const bookedActivities = activities.filter((activity) => currentState.get(activity.id) === 'BOOKED');
  const completedActivities = activities.filter((activity) => ['COMPLETED', 'RATED'].includes(currentState.get(activity.id)));

  return (
    <main className="min-h-[calc(100vh-4rem)] text-charcoal-900 pb-12">
      <section className="border-b border-ivory-300 bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <p className="text-xs font-bold uppercase tracking-wider text-forest-700">Your stay, thoughtfully planned</p>
          <h1 className="mt-1 text-2xl md:text-3xl font-bold text-charcoal-900 flex items-center gap-3">
            <Sparkles className="w-7 h-7 text-forest-700" />
            Recommended for You
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-charcoal-600">
            Suggestions use your current stay, recorded activity choices, listed availability, and guest ratings. No guest identities are shown.
          </p>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-800 font-medium">{error}</div>}
        {message && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-sm text-emerald-800 font-semibold">{message}</div>}

        {!token ? (
          <>
            <section className="mx-auto max-w-lg surface p-8 rounded-2xl border border-ivory-300 shadow-sm">
              <div className="mb-6 flex items-center gap-2">
                <LogIn className="w-5 h-5 text-forest-700" />
                <h2 className="text-lg font-bold text-charcoal-900">Guest sign in</h2>
              </div>
              <div className="mb-6 inline-flex rounded-lg border border-ivory-300 p-1 bg-ivory-50 w-full" role="tablist" aria-label="Guest sign-in method">
                <button
                  type="button"
                  role="tab"
                  aria-selected={loginMode === 'account'}
                  onClick={() => setLoginMode('account')}
                  className={`flex-1 rounded-md py-1.5 text-xs font-bold transition ${loginMode === 'account' ? 'bg-forest-800 text-white shadow-sm' : 'text-charcoal-600 hover:text-charcoal-900'}`}
                >
                  Guest account
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={loginMode === 'stay'}
                  onClick={() => setLoginMode('stay')}
                  className={`flex-1 rounded-md py-1.5 text-xs font-bold transition ${loginMode === 'stay' ? 'bg-forest-800 text-white shadow-sm' : 'text-charcoal-600 hover:text-charcoal-900'}`}
                >
                  Verify active stay
                </button>
              </div>

              {loginMode === 'account' ? (
                <form onSubmit={handleGuestLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Email</label>
                    <input
                      required
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      autoComplete="username"
                      className="w-full bg-white border border-ivory-300 rounded-lg px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Password</label>
                    <input
                      required
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete="current-password"
                      className="w-full bg-white border border-ivory-300 rounded-lg px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    />
                  </div>
                  <div className="rounded-lg bg-brass-50 border border-brass-200 px-3.5 py-2.5 text-xs text-brass-900 font-medium">
                    Demo account: <span className="font-mono font-bold">guest.demo@resort360.com</span> / <span className="font-mono font-bold">guest123</span>
                  </div>
                  <button
                    disabled={loading}
                    className="w-full py-2.5 bg-forest-800 hover:bg-forest-900 text-white font-bold rounded-lg shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <LogIn className="w-4 h-4" />{loading ? 'Signing in...' : 'Sign in'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleSession} className="space-y-4">
                  <p className="text-xs text-charcoal-600">Use the room number and guest name on an active reservation.</p>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Room number</label>
                    <input
                      required
                      maxLength="50"
                      value={roomNumber}
                      onChange={(event) => setRoomNumber(event.target.value)}
                      placeholder="e.g., 301"
                      className="w-full bg-white border border-ivory-300 rounded-lg px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Guest name</label>
                    <input
                      required
                      minLength="2"
                      maxLength="255"
                      value={guestName}
                      onChange={(event) => setGuestName(event.target.value)}
                      placeholder="Your name"
                      className="w-full bg-white border border-ivory-300 rounded-lg px-3.5 py-2 text-sm text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    />
                  </div>
                  <button
                    disabled={loading}
                    className="w-full py-2.5 bg-forest-800 hover:bg-forest-900 text-white font-bold rounded-lg shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <LogIn className="w-4 h-4" />{loading ? 'Checking stay...' : 'Continue'}
                  </button>
                </form>
              )}
            </section>
            <div className="mx-auto flex max-w-lg flex-wrap items-center justify-between gap-3 border-t border-ivory-300 pt-4">
              <p className="text-xs text-charcoal-600 font-medium">Need help during your stay?</p>
              <Link to="/guest-request" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-ivory-300 rounded-lg text-xs font-bold text-charcoal-800 hover:bg-ivory-50 shadow-sm">
                <QrCode className="h-4 w-4 text-forest-700" />Guest Request
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ivory-300 pb-4">
              <div>
                <p className="text-base font-bold text-charcoal-900">Welcome{guest?.name ? `, ${guest.name}` : ''}</p>
                <p className="mt-0.5 text-xs text-charcoal-500">{profile?.total_stays || 0} recorded stays · party size {profile?.average_party_size || 1}</p>
              </div>
              <button
                type="button"
                onClick={() => { setToken(''); setGuest(null); setProfile(null); setRecommendations([]); setActivities([]); setRequests([]); sessionStorage.removeItem('guestToken'); sessionStorage.removeItem('guestAccount'); window.dispatchEvent(new Event('guest-session-changed')); }}
                className="px-3 py-1.5 bg-white border border-ivory-300 rounded-lg text-xs font-bold text-charcoal-700 hover:bg-ivory-50 shadow-sm"
              >
                Sign out
              </button>
            </div>

            <nav className="flex flex-wrap gap-2 border-b border-ivory-300 pb-3" aria-label="Guest portal sections">
              {[
                ['recommended', 'Recommended'],
                ['requests', `My Requests${requests.length ? ` (${requests.length})` : ''}`],
                ['activities', 'My Activities'],
                ['feedback', 'Feedback'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={activeTab === key}
                  onClick={() => setActiveTab(key)}
                  className={`rounded-lg px-4 py-2 text-xs font-bold transition ${activeTab === key ? 'bg-forest-800 text-white shadow-sm' : 'bg-white border border-ivory-300 text-charcoal-700 hover:bg-ivory-50'}`}
                >
                  {label}
                </button>
              ))}
            </nav>

            {activeTab === 'recommended' && (
              <section className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-base font-bold text-charcoal-900">Recommended for You</h2>
                  <span className="text-xs text-charcoal-500">Ranked from recorded history and current stay context</span>
                </div>
                {recommendations.length ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {recommendations.map((item) => {
                      const activity = item.activity;
                      const status = currentState.get(activity.id);
                      return (
                        <article key={activity.id} className="surface flex flex-col p-5 rounded-xl border border-ivory-300 shadow-sm">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-[10px] font-bold uppercase tracking-wider text-forest-700">{activity.category}</p>
                              <h3 className="mt-1 text-base font-bold text-charcoal-900">{activity.name}</h3>
                              {activity.is_training_sample && (
                                <span className="mt-1.5 inline-block text-[9px] uppercase font-bold text-brass-800 bg-brass-50 border border-brass-200 rounded px-1.5 py-0.5">
                                  Demo sample
                                </span>
                              )}
                            </div>
                            <span className="shrink-0 text-xs font-semibold text-charcoal-600 bg-ivory-100 px-2 py-0.5 rounded">{activity.available_slots} places</span>
                          </div>
                          <p className="mt-2 text-xs leading-relaxed text-charcoal-700">{activity.description}</p>
                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-charcoal-600 font-medium">
                            <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5 text-forest-700" />{activity.crowd_level.toLowerCase()} crowd</span>
                            {activity.start_at && <span className="inline-flex items-center gap-1"><CalendarDays className="w-3.5 h-3.5 text-forest-700" />{new Date(activity.start_at).toLocaleString()}</span>}
                          </div>
                          <div className="mt-4 border-t border-ivory-200 pt-3">
                            <p className="text-[10px] font-bold uppercase tracking-wider text-charcoal-500">Why this is suggested</p>
                            <ul className="mt-1.5 space-y-1">
                              {item.reasons.map((reason) => (
                                <li key={reason} className="text-xs text-charcoal-700">· {reason}</li>
                              ))}
                            </ul>
                          </div>
                          <div className="mt-auto pt-4">
                            {status === 'BOOKED' ? (
                              <p className="text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded p-2 text-center">Already in your plans ✓</p>
                            ) : (
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  disabled={workingId === activity.id || activity.available_slots < 1}
                                  onClick={() => recordInteraction(activity.id, 'VIEWED')}
                                  className="flex-1 rounded-lg border border-ivory-300 bg-white px-3 py-2 text-xs font-semibold text-charcoal-800 hover:bg-ivory-50 disabled:opacity-50"
                                >
                                  View details
                                </button>
                                <button
                                  type="button"
                                  disabled={workingId === activity.id || activity.available_slots < 1}
                                  onClick={() => recordInteraction(activity.id, 'BOOKED')}
                                  className="flex-1 rounded-lg bg-forest-800 hover:bg-forest-900 text-white px-3 py-2 text-xs font-bold shadow-sm transition disabled:opacity-50"
                                >
                                  {workingId === activity.id ? 'Updating...' : 'Book activity'}
                                </button>
                              </div>
                            )}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <div className="surface border border-dashed border-ivory-300 rounded-xl p-8 text-center">
                    <Sparkles className="mx-auto w-6 h-6 text-charcoal-400" />
                    <p className="mt-2 text-sm font-bold text-charcoal-800">No available activities to recommend yet</p>
                    <p className="mt-1 text-xs text-charcoal-500">The resort team will add activities and availability as they are confirmed.</p>
                  </div>
                )}
              </section>
            )}

            {activeTab === 'requests' && (
              <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.8fr)]">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <ClipboardList className="w-5 h-5 text-forest-700" />
                    <h2 className="text-base font-bold text-charcoal-900">My service requests</h2>
                  </div>
                  <div className="space-y-3">
                    {requests.length ? (
                      requests.map((request) => (
                        <article key={request.id} className="surface border border-ivory-300 p-4 rounded-xl shadow-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="text-sm font-bold text-charcoal-900">{request.request_type}</h3>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-bold uppercase text-forest-800 bg-forest-50 border border-forest-200 px-2 py-0.5 rounded">
                                {request.status.replace('_', ' ')}
                              </span>
                              {request.is_training_sample && (
                                <span className="text-[10px] uppercase font-bold text-brass-800 bg-brass-50 border border-brass-200 rounded px-1.5 py-0.5">
                                  Training
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="mt-2 text-xs text-charcoal-700 leading-relaxed">{request.description.replace('TRAINING SAMPLE: ', '')}</p>
                          <p className="mt-2 text-[11px] font-medium text-charcoal-500">{request.priority} · {new Date(request.created_at).toLocaleString()}</p>
                        </article>
                      ))
                    ) : (
                      <p className="surface border border-dashed border-ivory-300 rounded-xl p-6 text-sm text-charcoal-500 text-center">No requests for this stay yet.</p>
                    )}
                  </div>
                </div>

                <form onSubmit={submitRequest} className="surface border border-ivory-300 p-5 rounded-xl shadow-sm h-fit space-y-4">
                  <h2 className="text-sm font-bold text-charcoal-900">Create a request</h2>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Request type</label>
                    <select
                      value={requestForm.request_type}
                      onChange={(event) => setRequestForm({ ...requestForm, request_type: event.target.value })}
                      className="w-full rounded-lg border border-ivory-300 bg-white px-3 py-2 text-xs font-semibold text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    >
                      <option>Housekeeping/Towels</option>
                      <option>AC/Maintenance</option>
                      <option>F&B/Room Service</option>
                      <option>Amenities</option>
                      <option>Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Details</label>
                    <textarea
                      required
                      minLength="5"
                      maxLength="2000"
                      rows="3"
                      value={requestForm.description}
                      onChange={(event) => setRequestForm({ ...requestForm, description: event.target.value })}
                      placeholder="Describe your request..."
                      className="w-full rounded-lg border border-ivory-300 bg-white px-3 py-2 text-xs text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500 resize-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1">Priority</label>
                    <select
                      value={requestForm.priority}
                      onChange={(event) => setRequestForm({ ...requestForm, priority: event.target.value })}
                      className="w-full rounded-lg border border-ivory-300 bg-white px-3 py-2 text-xs font-semibold text-charcoal-900 focus:outline-none focus:ring-2 focus:ring-forest-500"
                    >
                      <option>LOW</option>
                      <option>MEDIUM</option>
                      <option>HIGH</option>
                    </select>
                  </div>
                  <button className="w-full rounded-lg bg-forest-800 hover:bg-forest-900 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition">
                    Send request
                  </button>
                </form>
              </section>
            )}

            {activeTab === 'activities' && (
              <section className="space-y-6">
                <div>
                  <h2 className="text-base font-bold text-charcoal-900 mb-3">Booked activities</h2>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {bookedActivities.length ? (
                      bookedActivities.map((activity) => (
                        <div key={activity.id} className="surface flex flex-wrap items-center justify-between gap-3 border border-ivory-300 p-4 rounded-xl shadow-sm">
                          <div>
                            <p className="font-bold text-sm text-charcoal-900">{activity.name}</p>
                            <p className="mt-0.5 text-xs text-charcoal-500">{activity.category} · {activity.available_slots} places listed</p>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              disabled={workingId === activity.id}
                              onClick={() => recordInteraction(activity.id, 'CANCELLED')}
                              className="rounded-lg border border-ivory-300 bg-white px-3 py-1.5 text-xs font-semibold text-charcoal-700 hover:bg-ivory-50"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={workingId === activity.id}
                              onClick={() => recordInteraction(activity.id, 'COMPLETED')}
                              className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 hover:bg-emerald-800 px-3 py-1.5 text-xs font-bold text-white shadow-sm"
                            >
                              <Check className="w-3.5 h-3.5" />Completed
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-charcoal-500 italic">No booked activities yet.</p>
                    )}
                  </div>
                </div>

                <div>
                  <h2 className="text-base font-bold text-charcoal-900 mb-3">Completed activities and ratings</h2>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {completedActivities.length ? (
                      completedActivities.map((activity) => (
                        <div key={activity.id} className="surface flex flex-wrap items-center justify-between gap-3 border border-ivory-300 p-4 rounded-xl shadow-sm">
                          <div>
                            <p className="font-bold text-sm text-charcoal-900">{activity.name}</p>
                            <p className="mt-0.5 text-xs text-charcoal-500">{activity.interaction_status === 'RATED' ? 'Rating recorded' : 'How was it?'}</p>
                          </div>
                          <div className="flex items-center gap-1" aria-label={`Rate ${activity.name}`}>
                            <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                            {[1, 2, 3, 4, 5].map((rating) => (
                              <button
                                key={rating}
                                type="button"
                                disabled={workingId === activity.id}
                                onClick={() => recordInteraction(activity.id, 'RATED', rating)}
                                className="px-2 py-1 text-xs font-bold text-charcoal-700 bg-ivory-100 hover:bg-ivory-200 rounded disabled:opacity-50"
                                aria-label={`${rating} stars`}
                              >
                                {rating}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-charcoal-500 italic">Completed activities will appear here.</p>
                    )}
                  </div>
                </div>
              </section>
            )}

            {activeTab === 'feedback' && (
              <section className="max-w-2xl surface border border-ivory-300 p-6 rounded-xl shadow-sm space-y-4">
                <div className="flex items-center gap-2">
                  <MessageSquareText className="w-5 h-5 text-forest-700" />
                  <h2 className="text-base font-bold text-charcoal-900">Share feedback</h2>
                </div>
                <p className="text-xs text-charcoal-600">Feedback is summarized into anonymous sentiment and topic counts for resort managers.</p>
                <form onSubmit={submitFeedback} className="space-y-3">
                  <textarea
                    required
                    minLength="5"
                    maxLength="2000"
                    rows="4"
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                    placeholder="Tell us about your experience..."
                    className="w-full rounded-lg border border-ivory-300 bg-white px-3.5 py-2.5 text-xs text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500 resize-none"
                  />
                  <button className="rounded-lg bg-forest-800 hover:bg-forest-900 px-4 py-2 text-xs font-bold text-white shadow-sm transition">
                    Send feedback
                  </button>
                </form>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
};

