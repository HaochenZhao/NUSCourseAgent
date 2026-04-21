"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Settings, Save, Globe, Key, Cpu, X, CheckCircle2 } from "lucide-react";

interface UserSettings {
  use_free_trial: boolean;
  openai_api_key?: string;
  openai_model?: string;
  openai_base_url?: string;
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsModal({ isOpen, onClose, token }: SettingsModalProps) {
  const [settings, setSettings] = useState<UserSettings>({
    use_free_trial: true,
    openai_api_key: "",
    openai_model: "",
    openai_base_url: "",
  });
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen && token) {
      fetchSettings();
    }
  }, [isOpen, token]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/users/me/settings`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (err) {
      console.error("Failed to fetch settings", err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/users/me/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-xl glass rounded-3xl p-8 relative"
      >
        <button 
          onClick={onClose}
          className="absolute top-6 right-6 text-slate-500 hover:text-white"
        >
          <X size={20} />
        </button>

        <div className="flex items-center gap-3 mb-8">
          <div className="p-2.5 rounded-xl bg-indigo-500/15">
            <Settings className="text-indigo-400 w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-white">Agent Settings</h2>
        </div>

        <div className="space-y-6">
          {/* Mode Toggle */}
          <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-white font-medium text-sm">Model Configuration</h3>
                <p className="text-slate-500 text-xs mt-0.5">Choose how you want to power the agent.</p>
              </div>
              <div className="flex bg-black/40 rounded-xl p-1">
                <button
                  onClick={() => setSettings({ ...settings, use_free_trial: true })}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                    settings.use_free_trial ? "bg-indigo-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  Free Trial
                </button>
                <button
                  onClick={() => setSettings({ ...settings, use_free_trial: false })}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                    !settings.use_free_trial ? "bg-indigo-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  Custom
                </button>
              </div>
            </div>

            {settings.use_free_trial ? (
              <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                <p className="text-xs text-indigo-300 leading-relaxed">
                  Currently using the default OpenRouter provider. This is free for NUS students, powered by models like Nemotron-3 or Gemma.
                </p>
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div>
                  <label className="flex items-center gap-2 text-[11px] font-medium text-slate-500 uppercase tracking-widest mb-1.5 ml-1">
                    <Key size={12} /> OpenAI API Key
                  </label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                    value={settings.openai_api_key || ""}
                    onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-500 uppercase tracking-widest mb-1.5 ml-1">
                      <Cpu size={12} /> Model
                    </label>
                    <input
                      type="text"
                      placeholder="gpt-4o"
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                      value={settings.openai_model || ""}
                      onChange={(e) => setSettings({ ...settings, openai_model: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-500 uppercase tracking-widest mb-1.5 ml-1">
                      <Globe size={12} /> Base URL
                    </label>
                    <input
                      type="text"
                      placeholder="https://api.openai.com/v1"
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                      value={settings.openai_base_url || ""}
                      onChange={(e) => setSettings({ ...settings, openai_base_url: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-10 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 bg-white/5 hover:bg-white/10 text-slate-400 font-medium py-3 rounded-2xl transition-all"
          >
            Close
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex-[2] bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-3 rounded-2xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
          >
            {saved ? (
              <>
                <CheckCircle2 size={18} />
                Settings Saved
              </>
            ) : (
              <>
                <Save size={18} />
                Save Changes
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
