'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, DollarSign } from 'lucide-react';

interface Grant {
  id: string;
  title: string;
  organization: string;
  deadline: string;
  amount: { min: number; max: number };
  score: number;
}

interface CalendarDay {
  date: Date;
  isCurrentMonth: boolean;
  grants: Grant[];
}

export default function GrantCalendarPage() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedGrant, setSelectedGrant] = useState<Grant | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGrants();
  }, []);

  const fetchGrants = async () => {
    try {
      const res = await fetch('/api/grants');
      const data = await res.json();

      if (res.ok) {
        setGrants(data.grants || []);
      } else {
        toast.error(data.error || 'Failed to load grants');
      }
    } catch (error) {
      toast.error('Failed to load grants');
    } finally {
      setLoading(false);
    }
  };

  const getDaysInMonth = (date: Date): CalendarDay[] => {
    const year = date.getFullYear();
    const month = date.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days: CalendarDay[] = [];

    // Previous month days
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
      const day = prevMonthLastDay - i;
      const dayDate = new Date(year, month - 1, day);
      days.push({
        date: dayDate,
        isCurrentMonth: false,
        grants: getGrantsForDate(dayDate),
      });
    }

    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      const dayDate = new Date(year, month, day);
      days.push({
        date: dayDate,
        isCurrentMonth: true,
        grants: getGrantsForDate(dayDate),
      });
    }

    // Next month days
    const remainingDays = 42 - days.length; // 6 weeks × 7 days = 42
    for (let day = 1; day <= remainingDays; day++) {
      const dayDate = new Date(year, month + 1, day);
      days.push({
        date: dayDate,
        isCurrentMonth: false,
        grants: getGrantsForDate(dayDate),
      });
    }

    return days;
  };

  const getGrantsForDate = (date: Date): Grant[] => {
    return grants.filter((grant) => {
      const grantDate = new Date(grant.deadline);
      return (
        grantDate.getFullYear() === date.getFullYear() &&
        grantDate.getMonth() === date.getMonth() &&
        grantDate.getDate() === date.getDate()
      );
    });
  };

  const changeMonth = (delta: number) => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() + delta, 1)
    );
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const days = getDaysInMonth(currentDate);
  const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const upcomingGrants = grants
    .filter((g) => new Date(g.deadline) >= new Date())
    .sort((a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime())
    .slice(0, 5);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Grant Calendar</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Visualize upcoming grant deadlines
              </p>
            </div>
            <a
              href="/grants"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
            >
              Back to Grants
            </a>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Calendar */}
          <div className="lg:col-span-2">
            <div className="border rounded-lg bg-card p-6">
              {/* Calendar Header */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">{monthName}</h2>
                <div className="flex gap-2">
                  <button
                    onClick={goToToday}
                    className="px-3 py-1.5 text-sm bg-secondary text-secondary-foreground rounded hover:bg-secondary/90"
                  >
                    Today
                  </button>
                  <button
                    onClick={() => changeMonth(-1)}
                    className="p-2 hover:bg-muted rounded transition"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => changeMonth(1)}
                    className="p-2 hover:bg-muted rounded transition"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Day Headers */}
              <div className="grid grid-cols-7 gap-2 mb-2">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                  <div
                    key={day}
                    className="text-center text-sm font-semibold text-muted-foreground py-2"
                  >
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-2">
                {days.map((day, i) => {
                  const isToday =
                    day.date.toDateString() === new Date().toDateString();
                  const hasGrants = day.grants.length > 0;

                  return (
                    <div
                      key={i}
                      className={`min-h-24 p-2 border rounded transition ${
                        !day.isCurrentMonth
                          ? 'bg-muted/50 text-muted-foreground'
                          : 'bg-background'
                      } ${isToday ? 'ring-2 ring-primary' : ''} ${
                        hasGrants ? 'cursor-pointer hover:border-primary' : ''
                      }`}
                    >
                      <div
                        className={`text-sm font-semibold mb-1 ${
                          isToday ? 'text-primary' : ''
                        }`}
                      >
                        {day.date.getDate()}
                      </div>
                      {hasGrants && (
                        <div className="space-y-1">
                          {day.grants.slice(0, 2).map((grant) => (
                            <button
                              key={grant.id}
                              onClick={() => setSelectedGrant(grant)}
                              className="w-full text-left px-2 py-1 bg-primary/10 hover:bg-primary/20 rounded text-xs truncate transition"
                              title={grant.title}
                            >
                              <div className="flex items-center gap-1">
                                <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                <span className="truncate">{grant.title}</span>
                              </div>
                            </button>
                          ))}
                          {day.grants.length > 2 && (
                            <div className="text-xs text-muted-foreground px-2">
                              +{day.grants.length - 2} more
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Selected Grant */}
            {selectedGrant && (
              <div className="border rounded-lg bg-card p-6">
                <div className="flex items-start justify-between mb-4">
                  <h3 className="font-bold">Selected Grant</h3>
                  <button
                    onClick={() => setSelectedGrant(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    ×
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <h4 className="font-semibold mb-1">{selectedGrant.title}</h4>
                    <p className="text-sm text-muted-foreground">
                      {selectedGrant.organization}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {new Date(selectedGrant.deadline).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <span>
                      ${selectedGrant.amount.min.toLocaleString()} - $
                      {selectedGrant.amount.max.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Match Score:</span>
                    <span className="px-2 py-1 bg-primary/10 text-primary rounded text-sm font-medium">
                      {selectedGrant.score}
                    </span>
                  </div>
                  <a
                    href={`/grants?id=${selectedGrant.id}`}
                    className="block w-full px-4 py-2 bg-primary text-primary-foreground rounded text-center hover:bg-primary/90 transition mt-4"
                  >
                    View Details
                  </a>
                </div>
              </div>
            )}

            {/* Upcoming Deadlines */}
            <div className="border rounded-lg bg-card p-6">
              <h3 className="font-bold mb-4">Upcoming Deadlines</h3>
              {upcomingGrants.length === 0 ? (
                <p className="text-sm text-muted-foreground">No upcoming grants</p>
              ) : (
                <div className="space-y-3">
                  {upcomingGrants.map((grant) => {
                    const daysUntil = Math.ceil(
                      (new Date(grant.deadline).getTime() - Date.now()) /
                        (1000 * 60 * 60 * 24)
                    );
                    const isUrgent = daysUntil <= 7;

                    return (
                      <button
                        key={grant.id}
                        onClick={() => setSelectedGrant(grant)}
                        className="w-full text-left p-3 border rounded hover:border-primary transition"
                      >
                        <div className="font-semibold text-sm mb-1 truncate">
                          {grant.title}
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">
                            {new Date(grant.deadline).toLocaleDateString()}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded font-medium ${
                              isUrgent
                                ? 'bg-red-500/10 text-red-500'
                                : 'bg-primary/10 text-primary'
                            }`}
                          >
                            {daysUntil}d left
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Legend */}
            <div className="border rounded-lg bg-card p-6">
              <h3 className="font-bold mb-4">Legend</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded ring-2 ring-primary" />
                  <span>Today</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-primary/10" />
                  <span>Has deadlines</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  <span>Grant deadline</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
