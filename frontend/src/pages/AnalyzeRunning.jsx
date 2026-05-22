import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProgressAgent from '../components/ProgressAgent.jsx';
import { mockAnalyze } from '../api/mockApi.js';
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
  insurance: {
    icon: '🛡️',
    name: '보증 Agent',
    subtitle: 'HUG 안심전세 가입 기준 확인',
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
  const [coordinator, setCoordinator] = useState('');
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const cancelled = useRef(false);

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

      setCoordinator('안전성 평가가 필요하군요. 전문가들을 호출할게요.');
      await sleep(600);
      if (cancelled.current) return;

      // 시세 Agent
      updateAgent('market', { status: 'running' });
      await appendLog('market', '국토부 실거래가 조회 중...', 600);
      await appendLog('market', '주변 거래 12건 분석...', 700);
      await appendLog('market', '전세가율 계산 완료', 500);
      updateAgent('market', { status: 'done' });

      // 등기부 Agent
      updateAgent('registry', { status: 'running' });
      await appendLog('registry', 'Solar Pro3가 PDF 분석 중...', 800);
      await appendLog('registry', '근저당 항목 확인 중...', 600);
      await appendLog('registry', '신탁 여부 확인 ✓', 350);
      await appendLog('registry', '압류·가압류 확인 ✓', 350);
      updateAgent('registry', { status: 'done' });

      // 보증 Agent
      updateAgent('insurance', { status: 'running' });
      await appendLog('insurance', '공시가격 조회 중...', 500);
      await appendLog('insurance', 'HUG 기준 적용 중...', 500);
      await appendLog('insurance', '가입 가능성 판정 완료', 500);
      updateAgent('insurance', { status: 'done' });

      // 구어체 변환 Agent
      updateAgent('conversational', { status: 'running', progress: 25 });
      await appendLog('conversational', 'Solar Pro3로 톤 변환 중...', 900, 60);
      await appendLog('conversational', '청년 친화적 문장으로 다듬는 중...', 700, 100);
      updateAgent('conversational', { status: 'done', progress: 100 });

      // Resolve result
      const result = await mockAnalyze(input);
      if (cancelled.current) return;
      sessionStorage.setItem('analysisResult', JSON.stringify(result));
      sessionStorage.setItem(
        'sajuUnlocked',
        result.saju_unlocked ? 'true' : 'false'
      );

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
