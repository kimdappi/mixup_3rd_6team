import { Link } from 'react-router-dom';
import { Rocket, ShieldCheck, Home } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-full flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-primary/12 text-4xl mb-6 shadow-card">
          🏠
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">
          운명하우스
        </h1>
        <p className="text-subtext mt-2 text-lg font-medium">DestinyHouse</p>

        <p className="mt-8 text-xl md:text-2xl font-semibold leading-snug">
          “친구처럼 설명하는
          <br />
          청년 전세 안전 컨설턴트”
        </p>

        <div className="my-10 h-px bg-black/10" />

        <div className="text-text/90 leading-relaxed space-y-2 text-lg">
          <p>전세사기 피해자 3명 중 2명이 청년이에요.</p>
          <p>등기부등본, 전세가율, 보증보험… 너무 어렵죠?</p>
          <p className="font-semibold mt-3">저희가 친구처럼 풀어드릴게요.</p>
        </div>

        <Link to="/analyze" className="btn-primary mt-10 text-lg px-8 py-4">
          <Rocket className="w-5 h-5" />
          내 매물 분석하기
        </Link>

        <div className="my-10 h-px bg-black/10" />

        <div className="flex flex-col items-center gap-2 text-subtext">
          <div className="inline-flex items-center gap-2 font-semibold text-text">
            <ShieldCheck className="w-5 h-5 text-primary" />
            공식 데이터 기반
          </div>
          <p className="text-sm">국토부 · HUG · 서울시 자료 활용</p>
        </div>

        <p className="mt-10 text-xs text-subtext flex items-center justify-center gap-1.5">
          <Home className="w-3.5 h-3.5" />
          본 서비스의 분석은 공공데이터 기반 참고용이에요.
        </p>
      </div>
    </div>
  );
}
