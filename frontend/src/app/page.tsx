"use client";

import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import { Send, BookOpen, Sparkles, LoaderCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Profile {
  programme: string;
  level: "undergraduate" | "postgraduate";
  year: number;
  pool_description: string;
  semester: number;
}

interface TimetableSlot {
  module_code: string;
  start: string;
  end: string;
}

interface TimetableData {
  feasible: boolean;
  conflicts: { module_a: string; module_b: string; slot: string }[];
  schedule: Record<string, TimetableSlot[]>;
  total_contact_hours: number;
  exam_dates?: Record<string, string>;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
  timetable?: TimetableData;
}

type StreamEventType = "tool_call" | "text_delta" | "timetable" | "error" | "done" | "unknown";

const API_BASE = "http://localhost:8000";

const MODULE_COLORS = [
  "#818cf8", "#f472b6", "#34d399", "#fbbf24",
  "#a78bfa", "#fb7185", "#22d3ee", "#a3e635",
];
const LOADING_MESSAGES = [
  "Contacting the course planner",
  "Looking up NUS module data",
  "Checking schedules and conflicts",
  "Preparing the final answer",
];

// ---------------------------------------------------------------------------
// Timetable visualization
// ---------------------------------------------------------------------------

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const HOUR_START = 8;
const HOUR_END = 22;

function Timetable({ data }: { data: TimetableData }) {
  const allModules = new Set<string>();
  for (const slots of Object.values(data.schedule)) {
    for (const s of slots) allModules.add(s.module_code);
  }
  const moduleList = Array.from(allModules);
  const colorMap: Record<string, string> = {};
  moduleList.forEach((m, i) => {
    colorMap[m] = MODULE_COLORS[i % MODULE_COLORS.length];
  });

  const visibleDays = DAYS;
  if (moduleList.length === 0) return null;

  const hourHeight = 48;
  const totalHours = HOUR_END - HOUR_START;

  function timeToOffset(t: string) {
    const [h, m] = t.split(":").map(Number);
    return ((h - HOUR_START) + m / 60) * hourHeight;
  }

  return (
    <div className="mt-4 rounded-xl glass overflow-x-auto">
      <div className="p-3 border-b border-white/10 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-300">
          Weekly Timetable ({data.total_contact_hours}h contact)
        </span>
        <div className="flex gap-3 flex-wrap">
          {moduleList.map((m) => (
            <span key={m} className="flex items-center gap-1 text-xs text-slate-300">
              <span
                className="w-3 h-3 rounded-sm inline-block"
                style={{ background: colorMap[m] }}
              />
              {m}
            </span>
          ))}
        </div>
      </div>
      <div className="flex" style={{ minWidth: visibleDays.length * 140 + 56 }}>
        {/* Time axis */}
        <div className="flex-shrink-0 w-14 border-r border-white/10">
          <div className="h-8" />
          {Array.from({ length: totalHours }, (_, i) => (
            <div
              key={i}
              className="text-xs text-slate-500 text-right pr-2 border-t border-white/5"
              style={{ height: hourHeight }}
            >
              {HOUR_START + i}:00
            </div>
          ))}
        </div>

        {/* Day columns */}
        {visibleDays.map((day) => (
          <div key={day} className="flex-1 min-w-[120px] border-r border-white/5 last:border-r-0">
            <div className="h-8 flex items-center justify-center text-xs font-medium text-slate-400 border-b border-white/10">
              {day.slice(0, 3)}
            </div>
            <div className="relative" style={{ height: totalHours * hourHeight }}>
              {Array.from({ length: totalHours }, (_, i) => (
                <div
                  key={i}
                  className="absolute w-full border-t border-white/5"
                  style={{ top: i * hourHeight }}
                />
              ))}
              {(data.schedule[day] || []).length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-[11px] text-slate-600">
                  Free
                </div>
              )}
              {(data.schedule[day] || []).map((slot, idx) => {
                const top = timeToOffset(slot.start);
                const height = timeToOffset(slot.end) - top;
                const bg = colorMap[slot.module_code] || "#6b7280";
                return (
                  <div
                    key={idx}
                    className="absolute left-1 right-1 rounded-md px-1.5 py-1 text-white text-xs font-medium overflow-hidden shadow-lg"
                    style={{ top, height, background: bg, minHeight: 24, opacity: 0.9 }}
                  >
                    <div className="truncate">{slot.module_code}</div>
                    {height > 30 && (
                      <div className="text-[10px] opacity-80">
                        {slot.start}-{slot.end}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [profile, setProfile] = useState<Profile>({
    programme: "",
    level: "postgraduate",
    year: 1,
    pool_description: "",
    semester: 1,
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentToolCall, setCurrentToolCall] = useState<string | null>(null);
  const [toolCallHistory, setToolCallHistory] = useState<string[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentToolCall, toolCallHistory]);

  const loadingHeadline = currentToolCall || LOADING_MESSAGES[Math.min(toolCallHistory.length, LOADING_MESSAGES.length - 1)];

  const sendMessage = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      const text = input.trim();
      if (!text || loading) return;

      const userMsg: ChatMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);
      setCurrentToolCall(null);
      setToolCallHistory([]);

      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const resp = await fetch(`${API_BASE}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, profile, history }),
        });

        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let assistantText = "";
        const toolCalls: string[] = [];
        let timetableData: TimetableData | undefined;
        let currentEventType: StreamEventType = "unknown";

        const processLine = (line: string) => {
          if (line.startsWith("event: ")) {
            currentEventType = line.slice(7).trim() as StreamEventType;
            return;
          }
          if (!line.startsWith("data: ")) return;

          const eventType = currentEventType;
          currentEventType = "unknown";

          let payload: Record<string, unknown>;
          try {
            const parsed = JSON.parse(line.slice(6));
            if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
              return;
            }
            payload = parsed as Record<string, unknown>;
          } catch {
            return;
          }

          if (eventType === "tool_call") {
            const display = String(payload.display || payload.name || "Running tool...");
            toolCalls.push(display);
            setToolCallHistory((prev) => [...prev, display]);
            setCurrentToolCall(display);
          } else if (eventType === "text_delta") {
            assistantText += String(payload.text || "");
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: assistantText,
                  toolCalls: [...toolCalls],
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantText,
                  toolCalls: [...toolCalls],
                });
              }
              return updated;
            });
            setCurrentToolCall("Writing response...");
          } else if (eventType === "timetable") {
            timetableData = payload as TimetableData;
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  timetable: timetableData,
                };
              }
              return updated;
            });
            setCurrentToolCall("Rendering timetable...");
          } else if (eventType === "error") {
            assistantText += `\n\n**Error:** ${String(payload.message || "Unknown error")}`;
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                updated[updated.length - 1] = { ...last, content: assistantText };
              } else {
                updated.push({ role: "assistant", content: assistantText });
              }
              return updated;
            });
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.trim()) processLine(line.trim());
          }
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `**Connection Error:** ${errorMessage}` },
        ]);
      } finally {
        setLoading(false);
        setCurrentToolCall(null);
        setToolCallHistory([]);
      }
    },
    [input, loading, messages, profile]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 glass border-r border-white/10 flex flex-col">
        <div className="p-5 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <BookOpen className="text-indigo-400 w-7 h-7" />
            <h1 className="text-lg font-bold gradient-text">NUS Course Agent</h1>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 ml-9.5">AI-powered course selection</p>
        </div>

        <div className="p-5 flex-1 overflow-y-auto space-y-5">
          {/* Programme */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">Programme</label>
            <input
              type="text"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              placeholder="e.g. MComp Computer Science"
              value={profile.programme}
              onChange={(e) => setProfile({ ...profile, programme: e.target.value })}
            />
          </div>

          {/* Level */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">Level</label>
            <div className="flex gap-2">
              {(["undergraduate", "postgraduate"] as const).map((lvl) => (
                <button
                  key={lvl}
                  className={`flex-1 text-xs py-2 rounded-lg border transition-all duration-200 ${
                    profile.level === lvl
                      ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20"
                      : "bg-white/5 text-slate-400 border-white/10 hover:bg-white/10"
                  }`}
                  onClick={() => setProfile({ ...profile, level: lvl })}
                >
                  {lvl === "undergraduate" ? "Undergrad" : "Postgrad"}
                </button>
              ))}
            </div>
          </div>

          {/* Year */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">Year of Study</label>
            <input
              type="number"
              min={1}
              max={6}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              value={profile.year}
              onChange={(e) => setProfile({ ...profile, year: parseInt(e.target.value) || 1 })}
            />
          </div>

          {/* Eligible courses */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">Eligible Courses</label>
            <textarea
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none"
              rows={3}
              placeholder="e.g. All CS-prefixed courses offered by SoC"
              value={profile.pool_description}
              onChange={(e) => setProfile({ ...profile, pool_description: e.target.value })}
            />
          </div>

          {/* Semester */}
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">Semester</label>
            <div className="flex gap-2">
              {[1, 2].map((s) => (
                <button
                  key={s}
                  className={`flex-1 text-sm py-2 rounded-lg border transition-all duration-200 ${
                    profile.semester === s
                      ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/20"
                      : "bg-white/5 text-slate-400 border-white/10 hover:bg-white/10"
                  }`}
                  onClick={() => setProfile({ ...profile, semester: s })}
                >
                  Sem {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col min-w-0 bg-white/[0.02]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm">
              <div className="text-center">
                <Sparkles className="w-8 h-8 text-indigo-400/50 mx-auto mb-3" />
                <p className="text-lg mb-1 text-slate-300">Welcome to NUS Course Agent</p>
                <p className="text-slate-500">Fill in your profile on the left, then ask for course recommendations.</p>
              </div>
            </div>
          )}

          <div className="max-w-3xl mx-auto space-y-4">
            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Tool call indicators */}
                  {msg.role === "assistant" && msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1.5">
                      {msg.toolCalls.map((tc, j) => (
                        <span
                          key={j}
                          className="inline-flex items-center gap-1.5 text-xs text-slate-400 bg-white/5 border border-white/10 rounded-full px-2.5 py-0.5"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          {tc}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Message bubble */}
                  <div
                    className={`rounded-xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-indigo-600 text-white ml-auto max-w-xl rounded-tr-none"
                        : "glass rounded-tl-none"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="prose text-sm">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Timetable */}
                  {msg.timetable && <Timetable data={msg.timetable} />}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading indicator */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass rounded-xl border border-indigo-400/20 px-4 py-3"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-full bg-indigo-500/15 p-2 text-indigo-300">
                    <LoaderCircle size={18} className="animate-spin" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="text-sm font-medium text-slate-100">{loadingHeadline}</p>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      The request is still running. Long searches can take a while when module lookup,
                      prerequisite checks, and timetable generation happen in sequence.
                    </p>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/5">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-400 via-cyan-300 to-indigo-400"
                        animate={{ x: ["-35%", "105%"] }}
                        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                        style={{ width: "38%" }}
                      />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(toolCallHistory.length > 0 ? toolCallHistory : ["Waiting for first SSE update..."]).map((step, i) => (
                        <span
                          key={`${step}-${i}`}
                          className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-300"
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          {step}
                        </span>
                      ))}
                      {currentToolCall && (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-400/20 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-200">
                          <Sparkles size={12} className="animate-pulse" />
                          {currentToolCall}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="px-8 py-4">
          <form onSubmit={sendMessage} className="max-w-3xl mx-auto">
            <div className="glass rounded-2xl flex items-end gap-3 p-2 pl-4 shadow-2xl shadow-indigo-500/10">
              <textarea
                ref={inputRef}
                className="flex-1 bg-transparent border-none px-1 py-2 text-sm text-slate-200 placeholder:text-slate-500 resize-none focus:outline-none"
                rows={2}
                placeholder="Ask for course recommendations..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed p-3 rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/20"
              >
                <Send size={18} className="text-white" />
              </button>
            </div>
            <p className="text-center text-[10px] text-slate-600 mt-2 uppercase tracking-[0.15em]">
              Press Enter to send &middot; Shift+Enter for new line
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
