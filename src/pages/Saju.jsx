import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles } from 'lucide-react';
import ConversationalBox from '../components/ConversationalBox.jsx';
import OhengChart from '../components/OhengChart.jsx';
import { mockSajuMatch } from '../api/mockApi.js';

export default function Saju() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState('input'); // 'input' | 'loading' | 'result'
  const [form, setForm] = useState({
    year: '',
    month: '',
    day: '',
    hour: '',
    minute: '',
    city: '',
  });
  const [result, setResult] = useState(null);

  useEffect(() => {
    const unlocked = sessionStorage.getItem('sajuUnlocked') === 'true';
    if (!unlocked) {
      navigate('/result');
    }
  }, [navigate]);

  function update(k, v) {
    const numericKeys = ['year', 'month', 'day', 'hour', 'minute'];
    const next = numericKeys.includes(k) ? v.replace(/[^\d]/g, '') : v;
    setForm((prev) => ({ ...prev, [k]: next }));
  }

  const canSubmit =
    Number(form.year) >= 1900 &&
    Number(form.month) >= 1 &&
    Number(form.month) <= 12 &&
    Number(form.day) >= 1 &&
    Number(form.day) <= 31;

  async function onSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setPhase('loading');
    const r = await mockSajuMatch({
      year: Number(form.year),
      month: Number(form.month),
      day: Number(form.day),
      hour: Number(form.hour) || 0,
      minute: Number(form.minute) || 0,
      city: form.city.trim(),
    });
    setResult(r);
    setPhase('result');
  }

  return (
    <div className="min-h-full px-6 py-8 md:py-12">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Link to="/result" className="btn-ghost">
            <ArrowLeft className="w-4 h-4" />
            리포트로
          </Link>
          <Link to="/" className="font-bold text-bonus">
            🔮 사주 매칭
          </Link>
        </div>

        {phase === 'input' && (
          <SajuInputView
            form={form}
            update={update}
            onSubmit={onSubmit}
            canSubmit={canSubmit}
          />
        )}

        {phase === 'loading' && (
          <div className="card text-center py-16">
            <Sparkles className="w-8 h-8 text-bonus mx-auto animate-pulse" />
            <p className="mt-4 text-subtext">사주 정보를 풀이하는 중이에요...</p>
          </div>
        )}

        {phase === 'result' && result && <SajuResultView result={result} />}

        <p className="mt-10 text-xs text-subtext text-center">
          ⚠️ 사주는 전통 문화 콘텐츠로 제공돼요. 계약 결정은 안전성 분석을 우선해주세요.
        </p>
      </div>
    </div>
  );
}

function SajuInputView({ form, update, onSubmit, canSubmit }) {
  return (
    <>
      <h1 className="text-2xl md:text-3xl font-extrabold">
        🎁 보너스: 사주 궁합 매칭
      </h1>
      <div className="mt-2 h-1 w-16 bg-bonus rounded-full" />

      <p className="mt-6 text-text/90 leading-relaxed">
        안전한 매물을 찾으셨네요! 👏
        <br />
        이제 좀 재미있는 분석도 해볼까요?
      </p>
      <p className="mt-2 text-subtext">🔮 사주로 이 집과의 궁합을 봐드려요</p>

      <form onSubmit={onSubmit} className="card mt-8 space-y-6">
        <div>
          <label className="block font-semibold mb-2">📅 생년월일</label>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="text"
              inputMode="numeric"
              placeholder="1998"
              maxLength={4}
              value={form.year}
              onChange={(e) => update('year', e.target.value)}
              className="input-field text-center"
            />
            <input
              type="text"
              inputMode="numeric"
              placeholder="6"
              maxLength={2}
              value={form.month}
              onChange={(e) => update('month', e.target.value)}
              className="input-field text-center"
            />
            <input
              type="text"
              inputMode="numeric"
              placeholder="15"
              maxLength={2}
              value={form.day}
              onChange={(e) => update('day', e.target.value)}
              className="input-field text-center"
            />
          </div>
        </div>

        <div>
          <label className="block font-semibold mb-2">🕐 태어난 시간 (대략이라도)</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              inputMode="numeric"
              placeholder="시 (예: 14)"
              maxLength={2}
              value={form.hour}
              onChange={(e) => update('hour', e.target.value)}
              className="input-field text-center"
            />
            <input
              type="text"
              inputMode="numeric"
              placeholder="분 (예: 30)"
              maxLength={2}
              value={form.minute}
              onChange={(e) => update('minute', e.target.value)}
              className="input-field text-center"
            />
          </div>
        </div>

        <div>
          <label className="block font-semibold mb-2">📍 태어난 지역</label>
          <input
            type="text"
            value={form.city}
            onChange={(e) => update('city', e.target.value)}
            placeholder="예: 서울"
            className="input-field"
          />
        </div>

        <p className="text-xs text-subtext">
          ⚠️ 재미·문화 콘텐츠예요. 결정은 본인 몫!
        </p>

        <button
          type="submit"
          disabled={!canSubmit}
          className="btn-primary w-full bg-bonus hover:brightness-110"
        >
          🔮 궁합 분석하기
        </button>
      </form>
    </>
  );
}

function SajuResultView({ result }) {
  return (
    <>
      <h1 className="text-2xl md:text-3xl font-extrabold">🔮 사주 궁합 결과</h1>
      <div className="mt-2 h-1 w-16 bg-bonus rounded-full" />

      <section className="mt-8 card text-center">
        <div className="text-subtext font-medium">궁합 점수</div>
        <div className="mt-2 text-5xl font-extrabold text-bonus">
          {result.match_score}
          <span className="text-2xl text-subtext font-bold"> / 100</span>
        </div>
        <div className="mt-2 text-text font-semibold">
          {result.match_grade} ✨
        </div>
        <div className="mt-4 text-sm text-subtext">{result.saju_pillars}</div>
      </section>

      <section className="card mt-6">
        <h3 className="font-bold mb-2">당신의 오행 분포</h3>
        <OhengChart data={result.oheng_distribution} />
        {result.lacking_oheng?.length > 0 && (
          <p className="mt-3 text-sm text-subtext">
            🌱 부족한 기운:{' '}
            <span className="font-semibold text-text">
              {result.lacking_oheng.join(', ')}
            </span>
          </p>
        )}
      </section>

      <section className="mt-6">
        <ConversationalBox title="이 집과의 매칭" tone="bonus">
          {result.conversational}
        </ConversationalBox>
      </section>

      <section className="card mt-6">
        <h3 className="font-bold mb-3">매칭 상세</h3>
        <ul className="space-y-2">
          {result.match_details.map((d, i) => (
            <li
              key={i}
              className="flex items-center justify-between text-text"
            >
              <span>
                {d.points >= 0 ? '✓' : '△'} {d.factor}
              </span>
              <span
                className={`font-bold ${
                  d.points >= 0 ? 'text-bonus' : 'text-danger'
                }`}
              >
                {d.points > 0 ? `+${d.points}점` : `${d.points}점`}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <p className="mt-6 text-xs text-subtext">{result.disclaimer}</p>
    </>
  );
}
