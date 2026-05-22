import { useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ShieldAlert,
} from 'lucide-react';

const LEVEL_CFG = {
  safe: {
    label: '✅ 안전',
    pillColor: 'bg-success/12 text-success',
    icon: CheckCircle2,
  },
  caution: {
    label: '🟡 주의',
    pillColor: 'bg-warning/15 text-warning',
    icon: AlertTriangle,
  },
  high: {
    label: '🚨 위험',
    pillColor: 'bg-danger/12 text-danger',
    icon: AlertOctagon,
  },
  very_high: {
    label: '🚨 매우 위험',
    pillColor: 'bg-danger/15 text-danger font-bold',
    icon: ShieldAlert,
  },
};

function formatWonFromOrigin(won) {
  if (won == null) return '정보 없음';
  const n = Number(won);
  if (!Number.isFinite(n) || n === 0) return '0원';
  const man = Math.floor(n / 10000);
  const eok = Math.floor(man / 10000);
  const remainder = man % 10000;
  if (eok === 0) return `${man.toLocaleString()}만원`;
  if (remainder === 0) return `${eok}억`;
  return `${eok}억 ${remainder.toLocaleString()}만원`;
}

export default function RegistryAnalysisCard({ registryResult }) {
  const [open, setOpen] = useState(false);
  if (!registryResult) return null;

  const info = registryResult.info || {};
  const risk = registryResult.risk || {};
  const summary = registryResult.summary || '';

  const cfg = LEVEL_CFG[risk.risk_level] || LEVEL_CFG.caution;

  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📋</span>
          <h3 className="text-lg font-bold">등기부 분석</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${cfg.pillColor}`}>
          {cfg.label}
        </span>
      </div>

      <div className="text-text font-semibold">
        {info.has_mortgage
          ? `근저당권 ${info.mortgage_holder ? `(${info.mortgage_holder})` : ''} 설정됨`
          : '근저당권 없음'}
      </div>

      {summary && (
        <div className="bg-bg rounded-xl px-4 py-3 text-text leading-relaxed">
          “{summary}”
        </div>
      )}

      {/* 출처 안내 */}
      <p className="text-xs text-subtext">
        📡 Google Vision OCR + 룰 엔진 판정 (LLM은 자연어 풀이만 담당)
      </p>

      {/* 상세 보기 */}
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
            <li className="flex gap-2">
              <span className="text-primary">•</span>
              <span>위험도 코드: <b className="text-text">{risk.risk_signal}</b></span>
            </li>
            <li className="flex gap-2">
              <span className="text-primary">•</span>
              <span>판정 사유: {risk.rule_reason}</span>
            </li>
            <li className="flex gap-2">
              <span className="text-primary">•</span>
              <span>근저당권: {info.has_mortgage ? '있음' : '없음'}</span>
            </li>
            {info.max_claim_amount != null && (
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>채권최고액: {formatWonFromOrigin(info.max_claim_amount)}</span>
              </li>
            )}
            {info.mortgage_holder && (
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>근저당권자: {info.mortgage_holder}</span>
              </li>
            )}
            {risk.claim_to_deposit_ratio != null && (
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  채권최고액 / 전세금:{' '}
                  {(risk.claim_to_deposit_ratio * 100).toFixed(1)}%
                </span>
              </li>
            )}
            {info.address && (
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>등기부상 주소: {info.address}</span>
              </li>
            )}
            {info.owner_name && (
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>현재 소유자: {info.owner_name}</span>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
