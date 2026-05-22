const CONFIG = {
  A: { color: 'bg-success', label: '안전', icon: '✅' },
  B: { color: 'bg-warning', label: '주의', icon: '⚠️' },
  C: { color: 'bg-danger', label: '위험', icon: '🚨' },
  D: { color: 'bg-danger', label: '매우 위험', icon: '🚨' },
};

export default function RiskBadge({ grade, size = 'md' }) {
  const cfg = CONFIG[grade] || CONFIG.B;
  const sizeCls =
    size === 'lg'
      ? 'px-5 py-2.5 text-base'
      : size === 'sm'
      ? 'px-2.5 py-1 text-xs'
      : 'px-4 py-2 text-sm';

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full text-white font-bold ${cfg.color} ${sizeCls}`}
    >
      <span>{cfg.icon}</span>
      <span>{grade}</span>
      <span className="opacity-90 font-semibold">({cfg.label})</span>
    </div>
  );
}
