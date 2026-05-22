import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ProgressAgent from '../components/ProgressAgent.jsx';
import { mockAnalyze } from '../api/mockApi.js';
import { quickDiagnosis } from '../api/diagnosisApi.js';
import { mapQuickDiagnosis } from '../api/mapDiagnosis.js';
import { analyzeRegistry } from '../api/registryApi.js';
import { sleep } from '../utils/delay.js';

const INITIAL_AGENTS = {
  market: {
    icon: '📊',
    name: '시세 Agent',
    subtitle: '국토부 실거래가 기반 전세가율 분석',
    status: 'pending',
    progress: 0,
    logs: [],
    hideProgress: true,
  },
  registry: {
    icon: '📜',
    name: '등기부 Agent',
    subtitle: 'Solar Pro3가 PDF 분석',
    status: 'pending',
    progress: 0,
    logs: [],
    hideProgress: true,
  },
  conversational: {
    icon: '💬',
    name: '구어체 변환 Agent',
    subtitle: 'Solar Pro3가 친구처럼 풀어드릴게요',
    status: 'pending',
    progress: 0,
    logs: [],
  },
};

export default function AnalyzeRunning() {
  const navigate = useNavigate();
  const location = useLocation();
  const [coordinator, setCoordinator] = useState('');
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [errorMsg, setErrorMsg] = useState('');
  const cancelled = useRef(false);
  // AnalyzeInput에서 router state로 넘어온 File 객체 (없을 수도 있음)
  const pdfFile = location.state?.pdfFile || null;

  useEffect(() => {
    cancelled.current = false;

    function updateAgent(key, patch) {
      if (cancelled.current) return;
      setAgents((prev) => ({
        ...prev,
        [key]: { ...prev[key], ...patch },
      }));
    }

    async function appendLog(key, line, durationMs, finalProgress) {
      if (cancelled.current) return;
      setAgents((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          logs: [...prev[key].logs, line],
          progress: finalProgress ?? prev[key].progress,
        },
      }));
      await sleep(durationMs);
    }

    async function run() {
      const input = JSON.parse(sessionStorage.getItem('runtimeInput') || '{}');
      const isManual = input?.scenarioType === 'manual';

      setCoordinator(
        isManual
          ? '시세 진단을 시작할게요. 국토부 실거래가를 조회합니다.'
          : '안전성 평가가 필요하군요. 전문가들을 호출할게요.'
      );
      await sleep(600);
      if (cancelled.current) return;

      // 시세 Agent
      updateAgent('market', { status: 'running' });
      await appendLog('market', '국토부 실거래가 조회 중...', 500);

      let realResult = null;
      let realError = null;
      let registryResult = null;
      let registryError = null;

      if (isManual) {
        // 시세 진단과 등기부 분석을 병렬로 호출. 등기부는 PDF가 있을 때만.
        const diagPromise = quickDiagnosis({
          address: input.address,
          user_deposit: input.deposit,
          area_sqm: input.area_m2,
          housing_type: 'apt',
        });
        const registryPromise = pdfFile
          ? analyzeRegistry({ file: pdfFile, userDepositWon: input.deposit })
          : Promise.resolve(null);

        const [diagRes, regRes] = await Promise.allSettled([
          diagPromise,
          registryPromise,
        ]);
        if (diagRes.status === 'fulfilled') realResult = diagRes.value;
        else realError = diagRes.reason;
        if (regRes.status === 'fulfilled') registryResult = regRes.value;
        else registryError = regRes.reason;
      }
      if (cancelled.current) return;

      if (isManual && realError) {
        updateAgent('market', { status: 'error' });
        setErrorMsg(
          realError.detail || realError.message || '시세 진단 중 오류가 발생했어요.'
        );
        return;
      }

      if (isManual && realResult) {
        const m = realResult.market_analysis || {};
        await appendLog(
          'market',
          `근거 표본: ${m.scope} · 전세 ${m.jeonse_count}건 / 매매 ${m.trade_count}건`,
          600
        );
        await appendLog('market', `신뢰도: ${m.confidence}`, 400);
      } else {
        await appendLog('market', '주변 거래 12건 분석...', 700);
        await appendLog('market', '전세가율 계산 완료', 500);
      }
      updateAgent('market', { status: 'done' });

      if (!isManual) {
        // 시나리오 모드: 등기부 Agent 풀 시뮬레이션 (mock 데이터)
        updateAgent('registry', { status: 'running' });
        await appendLog('registry', 'Solar Pro3가 PDF 분석 중...', 800);
        await appendLog('registry', '근저당 항목 확인 중...', 600);
        await appendLog('registry', '신탁 여부 확인 ✓', 350);
        await appendLog('registry', '압류·가압류 확인 ✓', 350);
        updateAgent('registry', { status: 'done' });

      } else if (pdfFile && registryResult) {
        // 실 진단 모드 + PDF 업로드됨 + 분석 성공
        const risk = registryResult.risk || {};
        const info = registryResult.info || {};
        updateAgent('registry', { status: 'running' });
        await appendLog('registry', 'Google Vision OCR 추출 완료', 0);
        await appendLog(
          'registry',
          `근저당권: ${info.has_mortgage ? '있음' : '없음'}`,
          0,
        );
        if (info.max_claim_amount) {
          await appendLog(
            'registry',
            `채권최고액: ${info.max_claim_amount.toLocaleString()}원`,
            0,
          );
        }
        await appendLog('registry', `위험도: ${risk.risk_level}`, 0);
        updateAgent('registry', { status: 'done' });
      } else if (pdfFile && registryError) {
        // 업로드는 했는데 분석 실패
        updateAgent('registry', { status: 'error' });
        await appendLog(
          'registry',
          registryError.detail || registryError.message || '등기부 분석 실패',
          0,
        );
      } else {
        // PDF 미업로드
        updateAgent('registry', { status: 'skipped' });
      }

      // 구어체 변환 Agent
      updateAgent('conversational', { status: 'running', progress: 25 });
      await appendLog('conversational', 'Solar Pro3로 톤 변환 중...', 900, 60);
      await appendLog('conversational', '청년 친화적 문장으로 다듬는 중...', 700, 100);
      updateAgent('conversational', { status: 'done', progress: 100 });

      // Resolve result
      const result = isManual
        ? mapQuickDiagnosis(realResult, input)
        : await mockAnalyze(input);
      if (cancelled.current) return;
      sessionStorage.setItem('analysisResult', JSON.stringify(result));
      sessionStorage.setItem(
        'sajuUnlocked',
        result.saju_unlocked ? 'true' : 'false'
      );
      // 등기부 분석 결과는 별도 키로 저장 (Result.jsx의 RegistryAnalysisCard용)
      if (registryResult) {
        sessionStorage.setItem('registryResult', JSON.stringify(registryResult));
      } else {
        sessionStorage.removeItem('registryResult');
      }

      await sleep(500);
      if (cancelled.current) return;
      navigate('/result');
    }

    run();
    return () => {
      cancelled.current = true;
    };
  }, [navigate]);

  return (
    <div className="min-h-full px-6 py-8 md:py-12">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl md:text-3xl font-extrabold flex items-center gap-2">
          🤖 분석 중입니다... 잠시만요!
        </h1>
        <p className="mt-2 text-subtext">
          Multi-Agent가 협업해서 안전성을 점검하고 있어요.
        </p>

        <div className="mt-6 h-px bg-black/10" />

        {errorMsg && (
          <div className="mt-6 rounded-2xl border-2 border-danger/40 bg-danger/5 p-5">
            <div className="flex items-center gap-2 text-danger font-bold mb-2">
              🚨 시세 진단 실패
            </div>
            <p className="text-text/90 leading-relaxed">{errorMsg}</p>
            <p className="text-sm text-subtext mt-3">
              MOLIT_API_SERVICE_KEY 설정 또는 주소가 서울 25개 구에 속하는지 확인해주세요.
            </p>
          </div>
        )}

        {/* Coordinator */}
        <section className="my-8">
          <div className="card border border-primary/20">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🎯</span>
              <h3 className="font-bold">Coordinator Agent</h3>
            </div>
            <p className="text-text/90 leading-relaxed">
              {coordinator
                ? `“${coordinator}”`
                : '준비 중이에요...'}
            </p>
          </div>
        </section>

        <div className="space-y-4">
          {Object.entries(agents).map(([key, a]) => (
            <ProgressAgent
              key={key}
              icon={a.icon}
              name={a.name}
              subtitle={a.subtitle}
              status={a.status}
              progress={a.progress}
              logs={a.logs}
              hideProgress={a.hideProgress}
            />
          ))}
        </div>

        <p className="mt-10 text-xs text-subtext text-center">
          ⚠️ 분석은 공공데이터 기반 참고용이에요. 최종 결정은 전문가 상담을 권유해요.
        </p>
      </div>
    </div>
  );
}
