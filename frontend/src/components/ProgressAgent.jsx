import { Check, Loader2, MinusCircle, AlertOctagon } from 'lucide-react';

export default function ProgressAgent({
  icon = '🤖',
  name,
  subtitle,
  status = 'pending',
  progress = 0,
  logs = [],
  hideProgress = false,
}) {
  const isDone = status === 'done';
  const isRunning = status === 'running';
  const isPending = status === 'pending';
  const isSkipped = status === 'skipped';
  const isError = status === 'error';

  const bar = Math.max(0, Math.min(100, progress));

  return (
    <div
      className={`card transition-all duration-300 ${
        isRunning ? 'ring-2 ring-primary/40 shadow-ring animate-soft-pulse' : ''
      } ${isPending ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start gap-4">
        <div className="text-3xl shrink-0">{icon}</div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h4 className="font-bold text-text">{name}</h4>
              {subtitle && (
                <p className="text-sm text-subtext mt-0.5">{subtitle}</p>
              )}
            </div>
            <div className="shrink-0">
              {isDone && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-success/15 text-success text-sm font-semibold">
                  <Check className="w-4 h-4" /> 완료
                </span>
              )}
              {isRunning && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/15 text-primary text-sm font-semibold">
                  <Loader2 className="w-4 h-4 animate-spin" /> 진행 중
                </span>
              )}
              {isPending && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-black/5 text-subtext text-sm font-semibold">
                  대기
                </span>
              )}
              {isSkipped && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-black/5 text-subtext text-sm font-semibold">
                  <MinusCircle className="w-4 h-4" /> 이번 단계 생략
                </span>
              )}
              {isError && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-danger/15 text-danger text-sm font-semibold">
                  <AlertOctagon className="w-4 h-4" /> 실패
                </span>
              )}
            </div>
          </div>

          {!hideProgress && (
            <div className="mt-3 w-full h-2 rounded-full bg-black/5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isDone ? 'bg-success' : isRunning ? 'bg-primary' : 'bg-black/10'
                }`}
                style={{ width: `${isDone ? 100 : bar}%` }}
              />
            </div>
          )}

          {logs.length > 0 && (
            <ul className="mt-3 space-y-1.5 text-sm text-subtext">
              {logs.map((line, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 animate-fade-in-up"
                >
                  <span className="text-primary mt-1.5 w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
                  <span className="text-text/80">{line}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
