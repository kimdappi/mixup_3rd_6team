import { useState } from 'react';
import { ChevronDown, CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';

const GRADE_CFG = {
  safe: {
    label: '✅ 안전',
    pillColor: 'bg-success/12 text-success',
    barColor: 'bg-success',
    icon: CheckCircle2,
  },
  warning: {
    label: '⚠️ 주의',
    pillColor: 'bg-warning/15 text-warning',
    barColor: 'bg-warning',
    icon: AlertTriangle,
  },
  danger: {
    label: '🚨 위험',
    pillColor: 'bg-danger/12 text-danger',
    barColor: 'bg-danger',
    icon: AlertOctagon,
  },
};

export default function AnalysisCard({
  title,
  icon,
  grade = 'safe',
  headline,
  progressValue,
  conversational,
  details = [],
}) {
  const [open, setOpen] = useState(false);
  const cfg = GRADE_CFG[grade] || GRADE_CFG.safe;
  const safeProgress = Math.max(0, Math.min(100, progressValue ?? 0));

  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-bold">{title}</h3>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm font-bold ${cfg.pillColor}`}
        >
          {cfg.label}
        </span>
      </div>

      {headline && (
        <div className="text-text font-semibold">{headline}</div>
      )}

      {progressValue !== undefined && (
        <div className="w-full h-2.5 rounded-full bg-black/5 overflow-hidden">
          <div
            className={`h-full ${cfg.barColor} transition-all duration-700`}
            style={{ width: `${safeProgress}%` }}
          />
        </div>
      )}

      {conversational && (
        <div className="bg-bg rounded-xl px-4 py-3 text-text leading-relaxed">
          “{conversational}”
        </div>
      )}

      {details.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="btn-ghost text-sm"
          >
            <span>상세 보기</span>
            <ChevronDown
              className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
            />
          </button>
          {open && (
            <ul className="mt-2 space-y-1.5 text-sm text-subtext animate-fade-in-up">
              {details.map((d, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-primary">•</span>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
