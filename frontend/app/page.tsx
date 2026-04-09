"use client";

import { useState, useRef, useEffect } from "react";
import { Send, User, Bot, Search, Trash2, Settings, Sparkles, BookOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  role: "user" | "ai";
  content: string;
}

export default function CourseAgentPage() {
// ... existing state ...
  const [messages, setMessages] = useState<Message[]>([
    { role: "ai", content: "Hi! I'm your NUS Course Selection Agent. Tell me about your interests, or ask about a specific module." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [takenModules, setTakenModules] = useState<string[]>([]);
  const [newModule, setNewModule] = useState("");
  const [priority, setPriority] = useState("balanced");
  const [testStatus, setTestStatus] = useState<{success?: boolean, msg?: string}>({});
  const [testing, setTesting] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const testConnection = async () => {
    setTesting(true);
    setTestStatus({});
    try {
      const response = await fetch("http://localhost:8080/tools/test_llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "test", taken_modules: takenModules, priorities: priority })
      });
      const data = await response.json();
      if (data.success) {
        setTestStatus({ success: true, msg: `Connected to ${data.model}` });
      } else {
        setTestStatus({ success: false, msg: data.error || "Connection failed" });
      }
    } catch (e) {
      setTestStatus({ success: false, msg: "Backend unreachable" });
    } finally {
      setTesting(false);
    }
  };

  const scrollToBottom = () => {
// ... existing scrollToBottom ...
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8080/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          taken_modules: takenModules,
          priorities: priority
        })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = "";

      // Add a placeholder message for the AI
      setMessages(prev => [...prev, { role: "ai", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              aiContent += data.text;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = aiContent;
                return newMessages;
              });
            } catch (e) {
              console.error("Error parsing stream chunk", e);
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: "ai", content: "Sorry, I'm having trouble connecting to the backend. Make sure the FastAPI server is running." }]);
    } finally {
      setLoading(false);
    }
  };

  const addModule = () => {
    if (newModule && !takenModules.includes(newModule.toUpperCase())) {
      setTakenModules([...takenModules, newModule.toUpperCase()]);
      setNewModule("");
    }
  };

  const removeModule = (code: string) => {
    setTakenModules(takenModules.filter(m => m !== code));
  };

  return (
    <main className="flex h-screen max-w-[1600px] mx-auto overflow-hidden text-slate-200">
      {/* Sidebar / Profile Panel */}
      <aside className="w-80 glass border-r border-white/10 p-6 flex flex-col gap-6">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="text-indigo-400 w-8 h-8" />
          <h1 className="text-xl font-bold gradient-text">NUS Agent</h1>
        </div>

        <div>
          <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <User size={16} /> My Background
          </h2>
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. CS1010"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                value={newModule}
                onChange={(e) => setNewModule(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addModule()}
              />
              <button onClick={addModule} className="btn-primary p-2">
                <Search size={18} />
              </button>
            </div>
            <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-2">
              {takenModules.map(m => (
                <span key={m} className="bg-white/10 border border-white/10 rounded-full px-3 py-1 text-xs flex items-center gap-2 group hover:bg-white/20 transition-colors">
                  {m}
                  <button onClick={() => removeModule(m)} className="text-slate-500 hover:text-red-400">
                    <Trash2 size={12} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-white/10 space-y-4">
          <div>
            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Settings size={16} /> Preferences
            </h2>
            <select 
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="balanced">Balanced</option>
              <option value="knowledge-oriented">Knowledge Oriented</option>
              <option value="gpa-oriented">GPA Oriented</option>
              <option value="logistics-oriented">Lighter Workload</option>
            </select>
          </div>

          <div className="pt-2">
            <button 
              onClick={testConnection}
              disabled={testing}
              className={cn(
                "w-full text-xs py-2 rounded-lg border transition-all flex items-center justify-center gap-2",
                testStatus.success === true ? "border-green-500/50 text-green-400 bg-green-500/10" :
                testStatus.success === false ? "border-red-500/50 text-red-400 bg-red-500/10" :
                "border-white/10 text-slate-400 hover:bg-white/5"
              )}
            >
              <Sparkles size={14} className={testing ? "animate-spin" : ""} />
              {testing ? "Testing..." : "Test Connection"}
            </button>
            {testStatus.msg && (
              <p className={cn(
                "text-[10px] mt-2 text-center",
                testStatus.success ? "text-green-500/70" : "text-red-500/70"
              )}>
                {testStatus.msg}
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <section className="flex-1 flex flex-col relative bg-white/[0.02]">
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex gap-4 group",
                  m.role === "user" ? "flex-row-reverse" : ""
                )}
              >
                <div className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center shrink-0",
                  m.role === "ai" ? "bg-indigo-500/20 text-indigo-400" : "bg-slate-700 text-slate-300"
                )}>
                  {m.role === "ai" ? <Bot size={24} /> : <User size={24} />}
                </div>
                <div className={cn(
                  "chat-bubble",
                  m.role === "ai" ? "chat-bubble-ai" : "chat-bubble-user"
                )}>
                  <div className="prose prose-invert max-w-none text-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Sparkles size={20} className="animate-pulse" />
              </div>
              <div className="chat-bubble chat-bubble-ai italic">Expertly analyzing courses...</div>
            </motion.div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-8 pt-0 mt-auto">
          <div className="glass rounded-2xl flex items-center gap-4 p-2 pl-4 shadow-2xl shadow-indigo-500/10">
            <input
              type="text"
              placeholder="Ask anything about NUS courses..."
              className="flex-1 bg-transparent border-none focus:outline-none text-slate-200 placeholder:text-slate-500"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button 
              onClick={handleSend}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 p-3 rounded-xl transition-all duration-200"
            >
              <Send size={20} className="text-white" />
            </button>
          </div>
          <p className="text-center text-[10px] text-slate-600 mt-4 uppercase tracking-[0.2em]">
            Powered by NUSMods API & Gemini 1.5 Pro
          </p>
        </div>
      </section>
    </main>
  );
}
