import React, { useEffect, useRef } from 'react';
import { Terminal, RefreshCw } from 'lucide-react';

interface LiveTerminalProps {
  logs: string[];
  status?: string;
}

export const LiveTerminal: React.FC<LiveTerminalProps> = ({ logs, status = 'RUNNING' }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="rounded-xl overflow-hidden border border-slate-800 bg-[#060911] font-mono text-xs">
      {/* Terminal Header */}
      <div className="bg-[#0D121F] px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span className="text-slate-300 font-semibold">Rover Agent Process Stream</span>
        </div>
        <div className="flex items-center gap-2">
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
          <span className="text-[10px] uppercase tracking-wider font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
            {status}
          </span>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="p-4 h-64 overflow-y-auto space-y-1.5 text-slate-300">
        {logs.length === 0 ? (
          <p className="text-slate-500 italic">Initializing execution process stream...</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex gap-2 leading-relaxed">
              <span className="text-slate-600 select-none">$</span>
              <span className="text-slate-300">{log}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
