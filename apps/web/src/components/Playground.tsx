import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ShieldCheck, Zap, ServerCrash } from 'lucide-react';

export const Playground: React.FC = () => {
  const [isActive, setIsActive] = useState(false);

  return (
    <div className="w-full max-w-5xl mx-auto my-16 px-4">
      <div className="text-center mb-10 space-y-4">
        <h2 className="text-3xl md:text-5xl font-black text-foreground tracking-tight">
          Experience <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-rose-600 dark:from-cyan-400 dark:via-primary dark:to-purple-500 bg-clip-text text-transparent">Autonomous Security</span>
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
          Toggle the AI agent to see how Rover instantly detects and patches vulnerabilities in your codebase.
        </p>
      </div>

      <div className="glass-panel p-1 rounded-3xl overflow-hidden relative border border-slate-700/50 shadow-2xl">
        {/* Toggle Header */}
        <div className="bg-slate-900/60 p-4 border-b border-slate-700/50 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-t-[22px]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center">
              <Sparkles className={`w-5 h-5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
            </div>
            <div>
              <h3 className="text-white font-bold text-sm">Rover AI Agent</h3>
              <p className="text-slate-400 text-xs">{isActive ? 'Actively patching code...' : 'Agent is idle'}</p>
            </div>
          </div>
          
          <button 
            onClick={() => setIsActive(!isActive)}
            className={`relative inline-flex h-8 w-16 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 ${
              isActive ? 'bg-indigo-500' : 'bg-slate-700'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-7 w-7 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                isActive ? 'translate-x-8' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Code Environment */}
        <div className="p-6 bg-[#0d1117] relative min-h-[300px] overflow-hidden rounded-b-[22px] font-mono text-sm leading-relaxed">
          
          <AnimatePresence mode="wait">
            {!isActive ? (
              <motion.div
                key="vulnerable"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-rose-400 bg-rose-400/10 px-2 py-1 rounded text-xs flex items-center gap-1 font-sans font-bold border border-rose-400/20">
                    <ServerCrash className="w-3 h-3" /> Vulnerable Code
                  </span>
                </div>
                <div>
                  <span className="text-purple-400">def</span> <span className="text-blue-400">execute_query</span>(<span className="text-orange-400">user_input</span>):
                </div>
                <div className="pl-4">
                  <span className="text-slate-500"># Direct string interpolation - SQL Injection Risk</span><br/>
                  <span className="text-slate-300">query</span> = <span className="text-green-400">f"SELECT * FROM users WHERE username = '</span><span className="text-rose-400 font-bold bg-rose-400/20 px-1 rounded">{'{user_input}'}</span><span className="text-green-400">'"</span><br/>
                  <span className="text-slate-300">db.execute(query)</span>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="secure"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded text-xs flex items-center gap-1 font-sans font-bold border border-emerald-400/20">
                    <ShieldCheck className="w-3 h-3" /> Patched by Rover
                  </span>
                  <span className="text-indigo-400 bg-indigo-400/10 px-2 py-1 rounded text-xs flex items-center gap-1 font-sans font-bold border border-indigo-400/20">
                    <Zap className="w-3 h-3" /> 0.3s
                  </span>
                </div>
                <div>
                  <span className="text-purple-400">def</span> <span className="text-blue-400">execute_query</span>(<span className="text-orange-400">user_input</span>):
                </div>
                <div className="pl-4">
                  <span className="text-slate-500"># Use parameterized queries to prevent SQL injection</span><br/>
                  <span className="text-slate-300">query</span> = <span className="text-green-400">"SELECT * FROM users WHERE username = %s"</span><br/>
                  <span className="text-slate-300 bg-emerald-400/10 px-1 rounded border border-emerald-400/20 shadow-[0_0_10px_rgba(52,211,153,0.1)]">db.execute(query, (<span className="text-orange-400">user_input</span>,))</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>
    </div>
  );
};
