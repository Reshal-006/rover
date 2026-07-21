import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderGit2, 
  ShieldAlert, 
  GitPullRequest, 
  History, 
  BarChart3, 
  Settings,
  Sparkles,
  Bot,
  Lock,
  GitBranch,
  ChevronDown,
  LogOut
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { useRoverStore } from '../store/useRoverStore';

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'Repositories', icon: FolderGit2, path: '/repositories' },
  { label: 'Bug Explorer', icon: ShieldAlert, path: '/explorer' },
  { label: 'Pull Requests', icon: GitPullRequest, path: '/pull-requests' },
  { label: 'Analytics', icon: BarChart3, path: '/analytics' },
  { label: 'History', icon: History, path: '/history' },
  { label: 'Settings', icon: Settings, path: '/settings' },
];

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { activeRepository } = useRoverStore();


  return (
    <aside className="w-64 bg-black/10 backdrop-blur-2xl border-r border-white/5 flex flex-col justify-between h-screen sticky top-0 z-40 select-none overflow-y-auto shrink-0">
      <div>
        {/* Brand Header */}
        <div className="p-5 flex items-center gap-3 border-b border-slate-800/40">
          <div className="w-9 h-9 rounded-xl bg-zinc-900 border border-zinc-700/50 flex items-center justify-center shadow-md">
            <Bot className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-base tracking-tight text-white">Rover</span>
              <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-1.5 py-0.2 rounded-full">v2.0</span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium tracking-wide">Autonomous AI Developer</p>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-white/10 to-transparent text-white border-l-2 border-cyan-400 rounded-l-none'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border-l-2 border-transparent rounded-l-none'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Active Repository Widget */}
        {activeRepository && (
          <div className="mx-3 my-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/50">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2">Active Repository</span>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                <span className="text-xs font-bold text-white truncate max-w-[120px]">{activeRepository.name || activeRepository.full_name}</span>
              </div>
              <span className="flex items-center gap-1 text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                <Lock className="w-2.5 h-2.5" />
                {activeRepository.is_private ? 'Private' : 'Public'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-slate-400">
              <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded font-mono font-semibold">{activeRepository.language || 'Unknown'}</span>
              <span className="flex items-center gap-1 font-mono">
                <GitBranch className="w-3 h-3 text-slate-500" />
                {activeRepository.default_branch || 'main'}
              </span>
            </div>
          </div>
        )}
        {/* AI Agent Status Widget */}
        <div className="mx-3 my-2 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/50 relative overflow-hidden">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1.5">AI Agent Status</span>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50"></span>
            <span className="text-xs font-bold text-emerald-300">Autonomous Mode</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed mb-2">Agent is actively scanning & fixing issues.</p>
        </div>
      </div>

      {/* User Profile Footer & Sign Out */}
      {user && (
        <div className="p-4 border-t border-white/5 bg-transparent mt-auto">
          <div 
            onClick={logout}
            title="Click to Sign Out"
            className="flex items-center gap-3 p-1 rounded-xl transition-colors cursor-pointer group"
          >
            <img
              src={user.avatar_url}
              alt={user.name}
              className="w-9 h-9 rounded-full object-cover ring-2 ring-white/10"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            <div>
              <div className="text-sm font-bold text-white tracking-tight group-hover:text-rose-300 transition-colors">Reshal-006</div>
              <div className="text-[10px] font-medium text-slate-500 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <LogOut className="w-3 h-3 text-rose-400" />
                <span>Sign Out</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
