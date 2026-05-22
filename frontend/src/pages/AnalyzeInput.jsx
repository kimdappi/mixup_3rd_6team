import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Home,
  AlertTriangle,
  AlertOctagon,
  Upload,
  ArrowRight,
  FileText,
} from 'lucide-react';
import { formatDeposit, formatNumber, parseNumber } from '../utils/format.js';
import { SCENARIOS } from '../data/scenarios.js';

export default function AnalyzeInput() {
  const navigate = useNavigate();

  const [address, setAddress] = useState('');
  const [depositText, setDepositText] = useState('');
  const [areaText, setAreaText] = useState('');
  const [pdfName, setPdfName] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const deposit = parseNumber(depositText);
  const depositPreview = useMemo(() => formatDeposit(deposit), [deposit]);

  const canSubmit =
    address.trim().length > 0 &&
    deposit > 0 &&
    parseNumber(areaText) > 0;

  function startScenario(scenarioType) {
    const s = SCENARIOS[scenarioType];
    const input = {
      address: s.address,
      deposit: s.deposit,
      area_m2: s.area_m2,
      scenarioType,
      // 시나리오 칩은 데모용이라 PDF 업로드 상태와 무관
      pdf_uploaded: true,
      pdf_name: 'demo.pdf',
    };
    sessionStorage.setItem('runtimeInput', JSON.stringify(input));
    sessionStorage.setItem('scenarioType', scenarioType);
    navigate('/analyze/running');
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    const input = {
      address: address.trim(),
      deposit,
      area_m2: parseNumber(areaText),
      scenarioType: 'manual',
      pdf_uploaded: Boolean(pdfName),
      pdf_name: pdfName || null,
    };
    sessionStorage.setItem('runtimeInput', JSON.stringify(input));
    sessionStorage.setItem('scenarioType', 'manual');
    // 등기부 분석용 PDF File 객체는 sessionStorage에 못 담으므로 router state로 전달.
    // 페이지 새로고침 시 사라지지만 정상 흐름엔 충분하다.
    navigate('/analyze/running', { state: { pdfFile } });
  }

  function onPdfPick(file) {
    if (!file) return;
    setPdfName(file.name);
    setPdfFile(file);
  }

  return (
    <div className="min-h-full px-6 py-8 md:py-12">
      <div className="max-w-2xl mx-auto">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="btn-ghost">
            <ArrowLeft className="w-4 h-4" />
            뒤로
          </Link>
          <Link to="/" className="font-bold text-primary">
            🏠 운명하우스
          </Link>
        </div>

        <h1 className="text-2xl md:text-3xl font-extrabold">
          1단계: 매물 정보를 알려주세요
        </h1>
        <div className="mt-2 h-1 w-16 bg-primary rounded-full" />

        {/* Quick scenarios */}
        <section className="mt-8">
          <div className="flex items-center gap-2 text-subtext mb-3 font-medium">
            ⚡ 빠른 체험 — 샘플 매물로 바로 시작하기
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => startScenario('safe')}
              className="scenario-chip border-success/40 bg-success/5 hover:bg-success/10"
            >
              <div className="flex items-center gap-2 text-success">
                <Home className="w-5 h-5" />
                안전한 매물
              </div>
              <div className="text-xs text-subtext mt-1 font-normal">
                등급 A · 사주 잠금 해제
              </div>
            </button>
            <button
              type="button"
              onClick={() => startScenario('warning')}
              className="scenario-chip border-warning/40 bg-warning/5 hover:bg-warning/10"
            >
              <div className="flex items-center gap-2 text-warning">
                <AlertTriangle className="w-5 h-5" />
                주의 매물
              </div>
              <div className="text-xs text-subtext mt-1 font-normal">
                등급 B · 근저당 있음
              </div>
            </button>
            <button
              type="button"
              onClick={() => startScenario('danger')}
              className="scenario-chip border-danger/40 bg-danger/5 hover:bg-danger/10"
            >
              <div className="flex items-center gap-2 text-danger">
                <AlertOctagon className="w-5 h-5" />
                위험 매물
              </div>
              <div className="text-xs text-subtext mt-1 font-normal">
                등급 D · 신탁·고전세가율
              </div>
            </button>
          </div>
        </section>

        {/* Divider */}
        <div className="my-10 flex items-center gap-3 text-subtext">
          <div className="flex-1 h-px bg-black/10" />
          <span className="text-sm">또는 직접 입력</span>
          <div className="flex-1 h-px bg-black/10" />
        </div>

        {/* Manual form */}
        <form onSubmit={handleSubmit} className="card space-y-6">
          <div className="rounded-xl bg-primary/5 border border-primary/20 px-4 py-3 text-sm text-text/80">
            💡 실시간 시세 진단은 현재 <b>서울 25개 구의 아파트</b>만 정확히 지원돼요.
            (국토부 실거래가 데이터 범위)
          </div>

          <div>
            <label className="block font-semibold mb-2">📍 주소</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="예: 서울 강서구 가양동 ○○아파트"
              className="input-field"
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">💰 보증금 (전세금)</label>
            <div className="relative">
              <input
                type="text"
                inputMode="numeric"
                value={depositText ? formatNumber(depositText) : ''}
                onChange={(e) => setDepositText(e.target.value)}
                placeholder="260,000,000"
                className="input-field pr-14"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-subtext text-sm">
                원
              </span>
            </div>
            {depositPreview && (
              <p className="mt-2 text-sm text-primary font-medium">
                💡 입력값: “{depositPreview}”
              </p>
            )}
          </div>

          <div>
            <label className="block font-semibold mb-2">🏠 면적</label>
            <div className="relative">
              <input
                type="text"
                inputMode="numeric"
                value={areaText}
                onChange={(e) =>
                  setAreaText(e.target.value.replace(/[^\d.]/g, ''))
                }
                placeholder="45"
                className="input-field pr-12"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-subtext text-sm">
                ㎡
              </span>
            </div>
          </div>

          <div>
            <label className="block font-semibold mb-2">📄 등기부등본 (선택)</label>
            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                onPdfPick(e.dataTransfer.files?.[0]);
              }}
              className={`block w-full border-2 border-dashed rounded-xl px-6 py-8 text-center cursor-pointer transition ${
                dragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-black/15 hover:border-primary/60 hover:bg-primary/5'
              }`}
            >
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => onPdfPick(e.target.files?.[0])}
              />
              {pdfName ? (
                <div className="flex items-center justify-center gap-2 text-text font-medium">
                  <FileText className="w-5 h-5 text-primary" />
                  {pdfName}
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-subtext">
                  <Upload className="w-6 h-6" />
                  <span>📎 PDF 업로드 또는 클릭하여 첨부</span>
                </div>
              )}
            </label>
            <p className="mt-2 text-xs text-subtext">
              💡 없으면 직접 입력으로 진행돼요
            </p>
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="btn-primary w-full text-lg py-4"
          >
            분석 시작
            <ArrowRight className="w-5 h-5" />
          </button>
        </form>

        <p className="mt-6 text-xs text-subtext text-center">
          ⚠️ 이 분석은 공공데이터 기반 참고용이에요.
        </p>
      </div>
    </div>
  );
}
