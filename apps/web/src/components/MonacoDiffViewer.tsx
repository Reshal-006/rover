import React from 'react';
import { DiffEditor } from '@monaco-editor/react';

interface MonacoDiffViewerProps {
  originalCode: string;
  modifiedCode: string;
  language?: string;
  filename?: string;
}

export const MonacoDiffViewer: React.FC<MonacoDiffViewerProps> = ({
  originalCode,
  modifiedCode,
  language = 'python',
  filename = 'source_code.py'
}) => {
  return (
    <div className="rounded-xl overflow-hidden border border-slate-800 bg-[#0E131F]">
      <div className="bg-[#090D16] px-4 py-2 border-b border-slate-800 flex items-center justify-between">
        <span className="text-xs font-mono text-slate-400">{filename}</span>
        <span className="text-[11px] text-indigo-400 font-mono bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">Side-by-side Diff</span>
      </div>
      <div className="h-[380px]">
        <DiffEditor
          height="100%"
          language={language}
          original={originalCode}
          modified={modifiedCode}
          theme="vs-dark"
          options={{
            renderSideBySide: true,
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 12.5,
            scrollBeyondLastLine: false,
            smoothScrolling: true
          }}
        />
      </div>
    </div>
  );
};
