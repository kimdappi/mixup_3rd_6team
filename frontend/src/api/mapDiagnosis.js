/**
 * 백엔드 `/api/diagnoses/quick` 응답을 Result.jsx가 이해하는 스키마로 변환.
 *
 * 백엔드는 현재 시세 진단만 다루므로,
 * 등기부 카드는 `has_registry_analysis`를 false로 두어
 * Result.jsx에서 렌더 생략하게 한다.
 */

const DEPOSIT_STATUS_GRADE = {
  fair: 'safe',
  cheap: 'safe',
  slightly_high: 'warning',
  overpriced: 'warning',
  suspicious: 'warning',
};

const RISK_LEVEL_GRADE = {
  safe: 'safe',
  caution: 'warning',
  high: 'danger',
  very_high: 'danger',
};

const SEVERITY_RANK = { info: 0, caution: 1, warning: 2, critical: 3 };

function gradeOf(level) {
  // 시세·전세가율 grade 중 더 나쁜 쪽을 종합 등급으로.
  if (!level) return 'A';
  if (level === 'danger') return 'D';
  if (level === 'warning') return 'B';
  return 'A';
}

function gradeLevel(grade) {
  switch (grade) {
    case 'A': return '안전';
    case 'B': return '주의';
    case 'C': return '위험';
    case 'D': return '매우 위험';
    default:  return '판정 불가';
  }
}

function gradeScore(grade) {
  switch (grade) {
    case 'A': return 88;
    case 'B': return 64;
    case 'C': return 42;
    case 'D': return 28;
    default:  return 50;
  }
}

function worstGrade(a, b) {
  const order = { safe: 0, warning: 1, danger: 2 };
  return (order[a] ?? -1) >= (order[b] ?? -1) ? a : b;
}

function formatMillion(won) {
  if (!won && won !== 0) return null;
  const eok = Math.floor(won / 100_000_000);
  const man = Math.round((won % 100_000_000) / 10_000);
  if (eok === 0) return `${man.toLocaleString()}만 원`;
  if (man === 0) return `${eok}억 원`;
  return `${eok}억 ${man.toLocaleString()}만 원`;
}

function formatSample(s) {
  // 예: "가양강변아파트 · 84.5㎡ · 5층 · 2025.04 · 2억 5,000만 원"
  const parts = [];
  if (s.apt_name) parts.push(s.apt_name);
  if (s.area_sqm != null) parts.push(`${Number(s.area_sqm).toFixed(1)}㎡`);
  if (s.floor != null && s.floor !== '') parts.push(`${s.floor}층`);
  if (s.year && s.month) {
    const mm = String(s.month).padStart(2, '0');
    parts.push(`${s.year}.${mm}`);
  }
  const price = formatMillion(s.price_won);
  if (price) parts.push(price);
  return parts.join(' · ');
}

const SCOPE_LABEL = {
  complex: '동일 단지',
  dong: '같은 동',
  gu: '같은 시군구',
  gu_all: '시군구 전체',
};

/**
 * @param {object} resp  /api/diagnoses/quick 응답
 * @param {object} input AnalyzeInput에서 입력한 값 (deposit 등 표시용)
 */
export function mapQuickDiagnosis(resp, input) {
  const market = resp.market_analysis || {};
  const jeonse = resp.jeonse_ratio_analysis || {};
  const signals = Array.isArray(resp.risk_signals) ? resp.risk_signals : [];

  const marketGrade = DEPOSIT_STATUS_GRADE[market.deposit_status] || 'safe';
  const jeonseGrade = RISK_LEVEL_GRADE[jeonse.risk_level] || 'safe';
  const overallLevel = worstGrade(marketGrade, jeonseGrade);
  const grade = gradeOf(overallLevel);

  // 시세 카드 텍스트
  const ratio = jeonse.user_jeonse_rate;
  const headline = ratio != null
    ? `전세가율 ${(ratio * 100).toFixed(1)}% ${ratio >= 0.8 ? '(기준 80% 초과)' : '(기준 80% 이하)'}`
    : market.deposit_ratio != null
      ? `보증금이 인근 평균의 ${(market.deposit_ratio * 100).toFixed(0)}% 수준`
      : '시세 비교 데이터 부족';

  const marketDetails = [];
  if (market.avg_jeonse) {
    marketDetails.push(`국토부 전세 평균: ${formatMillion(market.avg_jeonse)}`);
  }
  if (market.avg_sale) {
    marketDetails.push(`국토부 매매 평균: ${formatMillion(market.avg_sale)}`);
  }
  marketDetails.push(
    `근거 표본: ${SCOPE_LABEL[market.scope] || market.scope} · 전세 ${market.jeonse_count}건 / 매매 ${market.trade_count}건`
  );
  if (market.confidence_reason) {
    marketDetails.push(`신뢰도: ${market.confidence} (${market.confidence_reason})`);
  }

  // 상세 보기: 근거가 된 실제 거래 표본 (최근순, 각 최대 10건)
  const rentSamples = Array.isArray(market.rent_samples) ? market.rent_samples : [];
  if (rentSamples.length > 0) {
    marketDetails.push(`📋 전세 표본 ${rentSamples.length}건 (최근순):`);
    for (const s of rentSamples) {
      marketDetails.push(`  · ${formatSample(s)}`);
    }
  }
  const tradeSamples = Array.isArray(market.trade_samples) ? market.trade_samples : [];
  if (tradeSamples.length > 0) {
    marketDetails.push(`📋 매매 표본 ${tradeSamples.length}건 (최근순):`);
    for (const s of tradeSamples) {
      marketDetails.push(`  · ${formatSample(s)}`);
    }
  }

  // 체크리스트는 백엔드 룰 엔진(`compose_checklist`)이 베이스 + 시그널을 합쳐서 내려준다.
  // 백엔드 응답이 비어 있는 (구버전 호환) 케이스만 시그널을 자체 추출해 폴백.
  let checklist = Array.isArray(resp.checklist) ? resp.checklist : [];
  if (checklist.length === 0) {
    const ranked = [...signals].sort(
      (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0)
    );
    checklist = ranked
      .map((s) => s.recommended_action)
      .filter((a) => a && a.trim().length > 0);
  }
  if (checklist.length === 0) {
    checklist = [
      '계약 당일 전입신고 + 확정일자 받기',
      '등기부등본 발급해 권리관계 확인',
    ];
  }

  const sajuUnlocked = grade === 'A' && market.confidence !== 'low';

  const pdfUploaded = Boolean(input?.pdf_uploaded);
  const pdfName = input?.pdf_name || null;

  // 등기부: PDF 업로드 여부에 따라 빈 데이터 상태를 다르게.
  // 백엔드에 OCR이 없으므로 어느 쪽이든 분석 결과는 비어 있다.
  const registryPlaceholder = {
    status: pdfUploaded ? 'pending_ocr' : 'no_file',
    pdf_name: pdfName,
    message: pdfUploaded
      ? `📎 "${pdfName}" 파일은 받았지만, 등기부 OCR 분석은 아직 연결되지 않았어요. 직접 등기부등본을 확인해주세요.`
      : '📂 등기부등본 PDF가 업로드되지 않았어요. 등기부 진단은 PDF를 업로드해야 제공돼요.',
  };

  return {
    address: resp.address,
    source: 'molit_realtime_trade',
    has_registry_analysis: false,
    registry_placeholder: registryPlaceholder,
    disclaimer: resp.disclaimer,
    missing_information: resp.missing_information || [],
    raw_signals: signals,

    overall_risk: {
      grade,
      score: gradeScore(grade),
      level: gradeLevel(grade),
      // Solar Pro 시세 리포트 카드 — 4항목 풀버전 (LLM 또는 stub)
      one_line_summary: resp.summary || '시세 진단이 완료되었어요.',
    },

    market_analysis: {
      average_market_price: market.avg_sale || market.avg_jeonse || 0,
      deposit: input?.deposit ?? 0,
      jeonse_ratio: ratio != null
        ? ratio
        : market.deposit_ratio != null
          ? market.deposit_ratio
          : 0,
      grade: marketGrade,
      // v3.1 — 시세 안전성 카드 인용 박스는 1줄 요약만. 4항목 풀버전은 위 카드와 중복이므로.
      conversational: resp.oneline || resp.summary || '',
      details: marketDetails,
    },

    checklist,

    saju_unlocked: sajuUnlocked,
    saju_lock_message: sajuUnlocked
      ? null
      : grade === 'A'
        ? '신뢰도가 낮아 사주 매칭은 보류했어요. 더 명확한 매물 정보로 다시 시도해보세요.'
        : '위험 신호가 있는 매물이라 사주 매칭은 잠겨있어요. 더 안전한 매물을 찾으시면 잠금 해제돼요!',
  };
}
