import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock, Unlock, RefreshCw, ArrowLeft } from 'lucide-react';
import RiskBadge from '../components/RiskBadge.jsx';
import ConversationalBox from '../components/ConversationalBox.jsx';
import AnalysisCard from '../components/AnalysisCard.jsx';

const GRADE_BG = {
  A: 'from-success/10 to-success/0',
  B: 'from-warning/10 to-warning/0',
  C: 'from-danger/10 to-danger/0',
  D: 'from-danger/15 to-danger/0',
};

export default function Result() {
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [checkedSet, setCheckedSet] = useState(new Set());

  useEffect(() => {
    const raw = sessionStorage.getItem('analysisResult');
    if (!raw) {
      navigate('/analyze');
      return;
    }
    setResult(JSON.parse(raw));
  }, [navigate]);

  const overall = result?.overall_risk;

  const overallTone = useMemo(() => {
    if (!overall) return 'primary';
    if (overall.grade === 'A') return 'primary';
    if (overall.grade === 'B') return 'warning';
    return 'danger';
  }, [overall]);

  if (!result) {
    return (
      <div className="min-h-full flex items-center justify-center text-subtext">
        결과를 불러오는 중...
      </div>
    );
  }

  function toggleCheck(i) {
    setCheckedSet((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <div className="min-h-full px-6 py-8 md:py-12">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Link to="/analyze" className="btn-ghost">
            <ArrowLeft className="w-4 h-4" />
            처음으로
          </Link>
          <Link to="/" className="font-bold text-primary">
            🏠 운명하우스
          </Link>
        </div>

        <header className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-extrabold">📋 분석 리포트</h1>
          <p className="mt-2 text-subtext">{result.address}</p>
        </header>

        {/* Overall risk */}
        <section
          className={`rounded-3xl shadow-card bg-gradient-to-b ${GRADE_BG[overall.grade] || ''} bg-white p-8 text-center`}
        >
          <div className="text-subtext font-medium">종합 위험도</div>
          <div className="mt-4 flex flex-col items-center gap-3">
            <RiskBadge grade={overall.grade} size="lg" />
            <div className="text-5xl font-extrabold mt-2">{overall.score}점</div>
            <div className="w-full max-w-md h-3 rounded-full bg-black/5 overflow-hidden mt-2">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  overall.grade === 'A'
                    ? 'bg-success'
                    : overall.grade === 'B'
                    ? 'bg-warning'
                    : 'bg-danger'
                }`}
                style={{ width: `${overall.score}%` }}
              />
            </div>
            <p className="text-sm text-subtext mt-1">레벨: {overall.level}</p>
          </div>
        </section>

        {/* One-liner */}
        <section className="mt-8">
          <ConversationalBox title="한 줄로 말하면" tone={overallTone}>
            {overall.one_line_summary}
          </ConversationalBox>
        </section>

        {/* Analysis cards */}
        <section className="mt-10 space-y-4">
          <AnalysisCard
            title="시세 안전성"
            icon="📊"
            grade={result.market_analysis.grade}
            headline={`전세가율 ${Math.round(result.market_analysis.jeonse_ratio * 100)}% ${
              result.market_analysis.jeonse_ratio > 0.8 ? '(기준 80% 초과)' : '(기준 80% 이하)'
            }`}
            progressValue={Math.round(result.market_analysis.jeonse_ratio * 100)}
            conversational={result.market_analysis.conversational}
            details={result.market_analysis.details}
          />

          <AnalysisCard
            title="등기부 위험도"
            icon="📜"
            grade={result.registry_analysis.grade}
            headline={
              result.registry_analysis.has_trust
                ? '🚨 신탁 표시 발견'
                : result.registry_analysis.mortgage_max > 0
                ? `근저당 ${Math.floor(result.registry_analysis.mortgage_max / 10000)}만 원`
                : '깨끗한 등기부'
            }
            conversational={result.registry_analysis.conversational}
            details={result.registry_analysis.details}
          />

          <AnalysisCard
            title="보증보험 가능성"
            icon="🛡️"
            grade={result.insurance_analysis.grade}
            headline={
              result.insurance_analysis.eligible
                ? '✅ 가입 가능'
                : '🚨 가입 어려움'
            }
            conversational={result.insurance_analysis.conversational}
            details={result.insurance_analysis.details}
          />
        </section>

        {/* Checklist */}
        <section className="card mt-10">
          <h3 className="text-lg font-bold mb-4">📋 꼭 하셔야 할 일</h3>
          <ul className="space-y-2">
            {result.checklist.map((item, i) => {
              const checked = checkedSet.has(i);
              return (
                <li key={i}>
                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleCheck(i)}
                      className="mt-1 w-5 h-5 accent-primary rounded"
                    />
                    <span
                      className={`text-text leading-relaxed transition ${
                        checked ? 'line-through text-subtext' : ''
                      }`}
                    >
                      {item}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </section>

        {/* Saju unlock area */}
        <section className="mt-10">
          {result.saju_unlocked ? (
            <div className="rounded-2xl border-2 border-bonus/40 bg-bonus/5 p-6 text-center">
              <div className="text-bonus font-bold mb-2 flex items-center justify-center gap-2">
                <Unlock className="w-5 h-5" /> 🎁 보너스 잠금 해제!
              </div>
              <p className="text-text/80 mb-4">
                안전한 매물이 확인되어, 사주 궁합 매칭을 보실 수 있어요.
              </p>
              <Link
                to="/result/saju"
                className="btn-primary bg-bonus hover:brightness-110"
              >
                🔓 사주 궁합 매칭 보기
              </Link>
            </div>
          ) : (
            <div className="rounded-2xl border-2 border-dashed border-black/15 bg-black/[0.02] p-6 text-center">
              <div className="text-subtext font-semibold mb-2 flex items-center justify-center gap-2">
                <Lock className="w-4 h-4" /> 사주 매칭은 잠겨있어요
              </div>
              <p className="text-sm text-subtext">
                {result.saju_lock_message}
              </p>
            </div>
          )}
        </section>

        <p className="mt-10 text-xs text-subtext text-center">
          ⚠️ 이 분석은 공공데이터 기반 참고용이에요. 최종 결정은 전문가 상담을 권유해요.
        </p>

        <div className="mt-8 text-center">
          <Link to="/analyze" className="btn-primary">
            <RefreshCw className="w-4 h-4" />
            다른 매물 분석하기
          </Link>
        </div>
      </div>
    </div>
  );
}
