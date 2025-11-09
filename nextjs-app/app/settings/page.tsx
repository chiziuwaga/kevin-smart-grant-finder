'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Upload, Save, Moon, Sun } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // Cron settings
  const [cronEnabled, setCronEnabled] = useState(false);
  const [cronSchedule, setCronSchedule] = useState<string[]>([]);
  const [selectedTime1, setSelectedTime1] = useState('09:00');
  const [selectedTime2, setSelectedTime2] = useState('18:00');

  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [notifyOnNewGrants, setNotifyOnNewGrants] = useState(true);
  const [notifyOnLowCredits, setNotifyOnLowCredits] = useState(true);
  const [lowCreditThreshold, setLowCreditThreshold] = useState(2);

  // Search preferences
  const [minGrantScore, setMinGrantScore] = useState(0.5);
  const [autoSaveHighScore, setAutoSaveHighScore] = useState(true);

  // Document upload
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);

  useEffect(() => {
    fetchSettings();
    fetchDocuments();

    // Check system theme
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDarkMode(isDark);
    if (isDark) document.documentElement.classList.add('dark');
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/user/settings');
      const data = await res.json();

      if (data.settings) {
        setCronEnabled(data.settings.cronEnabled);
        setCronSchedule(data.settings.cronSchedule || []);
        setEmailNotifications(data.settings.emailNotifications);
        setNotifyOnNewGrants(data.settings.notifyOnNewGrants);
        setNotifyOnLowCredits(data.settings.notifyOnLowCredits);
        setLowCreditThreshold(Number(data.settings.lowCreditThreshold));
        setMinGrantScore(Number(data.settings.minGrantScore));
        setAutoSaveHighScore(data.settings.autoSaveHighScore);

        if (data.settings.cronSchedule?.length > 0) {
          setSelectedTime1(data.settings.cronSchedule[0]);
          if (data.settings.cronSchedule.length > 1) {
            setSelectedTime2(data.settings.cronSchedule[1]);
          }
        }
      }
    } catch (error) {
      toast.error('Failed to load settings');
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Failed to load documents');
    }
  };

  const handleSave = async () => {
    setLoading(true);

    try {
      const schedule = cronEnabled ? [selectedTime1, selectedTime2].filter(Boolean) : [];

      const res = await fetch('/api/user/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cronEnabled,
          cronSchedule: schedule,
          emailNotifications,
          notifyOnNewGrants,
          notifyOnLowCredits,
          lowCreditThreshold,
          minGrantScore,
          autoSaveHighScore,
        }),
      });

      if (res.ok) {
        toast.success('Settings saved successfully!');
      } else {
        toast.error('Failed to save settings');
      }
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size must be less than 50MB');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', 'OTHER');

      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        toast.success('Document uploaded successfully!');
        fetchDocuments();
      } else {
        const data = await res.json();
        toast.error(data.error || 'Upload failed');
      }
    } catch (error) {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Settings</h1>
          <div className="flex gap-2">
            <button
              onClick={toggleDarkMode}
              className="p-2 border rounded-lg hover:bg-muted"
            >
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="px-4 py-2 border rounded-lg hover:bg-muted"
            >
              Back to Chat
            </button>
          </div>
        </div>

        <div className="space-y-6">
          {/* Automated Searches */}
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Automated Grant Searches</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Enable Automated Searches</div>
                  <div className="text-sm text-muted-foreground">
                    Run grant searches automatically (max 2 times per day)
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={cronEnabled}
                    onChange={(e) => setCronEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              {cronEnabled && (
                <div className="grid grid-cols-2 gap-4 pl-4 border-l-2 border-primary">
                  <div>
                    <label className="block text-sm font-medium mb-2">First Run Time</label>
                    <input
                      type="time"
                      value={selectedTime1}
                      onChange={(e) => setSelectedTime1(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Second Run Time (Optional)
                    </label>
                    <input
                      type="time"
                      value={selectedTime2}
                      onChange={(e) => setSelectedTime2(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Notifications</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Email Notifications</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={emailNotifications}
                    onChange={(e) => setEmailNotifications(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Notify on New Grants</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyOnNewGrants}
                    onChange={(e) => setNotifyOnNewGrants(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Notify on Low Credits</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyOnLowCredits}
                    onChange={(e) => setNotifyOnLowCredits(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Low Credit Threshold: ${lowCreditThreshold}
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={lowCreditThreshold}
                  onChange={(e) => setLowCreditThreshold(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* Search Preferences */}
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Search Preferences</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Minimum Grant Score: {minGrantScore.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={minGrantScore}
                  onChange={(e) => setMinGrantScore(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="text-sm text-muted-foreground mt-1">
                  Only show grants with score above {minGrantScore.toFixed(1)}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Auto-Save High-Score Grants</div>
                  <div className="text-sm text-muted-foreground">
                    Automatically save grants with score &gt; 0.8
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoSaveHighScore}
                    onChange={(e) => setAutoSaveHighScore(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Document Upload */}
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Documents</h2>
            <div className="space-y-4">
              <div>
                <label className="cursor-pointer">
                  <input
                    type="file"
                    onChange={handleFileUpload}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt"
                  />
                  <div className="border-2 border-dashed rounded-lg p-8 text-center hover:bg-muted transition">
                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <div className="font-medium">
                      {uploading ? 'Uploading...' : 'Click to upload document'}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      PDF, DOC, DOCX, TXT (Max 50MB)
                    </div>
                  </div>
                </label>
              </div>

              {documents.length > 0 && (
                <div className="space-y-2">
                  <div className="font-medium">Uploaded Documents</div>
                  {documents.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">{doc.originalName}</div>
                        <div className="text-sm text-muted-foreground">
                          {(doc.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {new Date(doc.createdAt).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
