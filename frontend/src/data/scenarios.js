export const SCENARIO_SAFE = {
  address: '서울 강서구 가양동 강변아파트 101동 802호',
  deposit: 250000000,
  area_m2: 50,

  overall_risk: {
    grade: 'A',
    score: 92,
    level: '안전',
    one_line_summary:
      '와, 좋은 매물 찾으셨네요! 전세가율도 낮고, 등기부도 깨끗하고, 보증보험까지 가입 가능해요. 거의 완벽한 조건이에요. 👍',
  },

  market_analysis: {
    average_market_price: 420000000,
    deposit: 250000000,
    jeonse_ratio: 0.595,
    grade: 'safe',
    conversational:
      '이 동네 비슷한 집들이 보통 4억 2천에 거래되고 있어요. 보증금 2억 5천이면 60% 수준인데, 정부 기준 80%보다 훨씬 안전한 구간이에요!',
    details: [
      '국토부 실거래가 최근 12건 평균: 4억 2천만 원',
      '전세가율 59.5% (정부 기준 80% 이하)',
      '같은 단지 최근 1년 가격 변동성 ±3%',
    ],
  },

  registry_analysis: {
    mortgage_max: 0,
    has_trust: false,
    has_seizure: false,
    grade: 'safe',
    conversational:
      '등기부도 깨끗해요. 근저당, 신탁, 압류 같은 위험 신호가 하나도 없어요. 이건 정말 보기 드물어요!',
    details: ['근저당: 없음', '신탁: 없음', '압류·가압류: 없음'],
  },

  insurance_analysis: {
    eligible: true,
    grade: 'safe',
    conversational:
      '보증보험 가입도 가능해요. 안전장치까지 더하면 거의 완벽한 매물이에요!',
    details: [
      'HUG 안심전세 가입 기준 충족',
      '공시가격 대비 보증금 비율 적정',
    ],
  },

  checklist: [
    '전세보증보험 가입 신청 (HUG 안심전세 앱)',
    '계약 당일 전입신고 + 확정일자 받기',
    '임대인 미납 국세 한 번 더 확인',
  ],

  saju_unlocked: true,
  saju_lock_message: null,
};

export const SCENARIO_WARNING = {
  address: '서울 강서구 화곡동 ○○빌라 2층',
  deposit: 260000000,
  area_m2: 45,

  overall_risk: {
    grade: 'B',
    score: 68,
    level: '주의',
    one_line_summary:
      '전세가율이 좀 높아서 살짝 위험한데, 보증보험 가입이 가능하니까 보험만 잘 들면 비교적 안전하게 갈 수 있어요. 다만 근저당 3천만 원은 꼭 확인해주세요!',
  },

  market_analysis: {
    average_market_price: 310000000,
    deposit: 260000000,
    jeonse_ratio: 0.84,
    grade: 'warning',
    conversational:
      '비슷한 집들이 보통 3억 1천에 거래되는데, 보증금 2억 6천이면 84% 수준이에요. 정부 기준 80%를 살짝 넘었어요. 주의가 필요한 구간이에요.',
    details: [
      '국토부 실거래가 평균: 3억 1천만 원',
      '전세가율 84% (정부 기준 80% 초과)',
      '깡통전세 가능성 약간 있음',
    ],
  },

  registry_analysis: {
    mortgage_max: 30000000,
    has_trust: false,
    has_seizure: false,
    grade: 'warning',
    conversational:
      '근저당 3천만 원이 있어요. 집주인이 은행에서 3천 빌렸다는 뜻이에요. 만약 경매로 가면 은행이 먼저 가져가니까, 보증보험 꼭 드셔야 해요.',
    details: [
      '근저당: 3천만 원 (○○은행)',
      '신탁: 없음',
      '압류·가압류: 없음',
    ],
  },

  insurance_analysis: {
    eligible: true,
    grade: 'safe',
    conversational:
      '좋은 소식! 보증보험 가입이 가능할 것 같아요. 이거 꼭 드세요. 보험만 들면 위에 있는 근저당 위험도 다 막아줘요.',
    details: [
      'HUG 안심전세 가입 기준 충족',
      '근저당 포함 채권 총액 기준 통과',
    ],
  },

  checklist: [
    '전세보증보험 가입 (HUG 안심전세 앱) - 필수!',
    '계약 당일 전입신고 + 확정일자',
    "특약사항에 '근저당 추가 설정 금지' 명시",
    '임대인 미납 국세 열람 신청',
  ],

  saju_unlocked: false,
  saju_lock_message:
    '위험도 B라 사주 매칭은 잠겨있어요. 더 안전한 매물을 찾으시면 잠금 해제돼요!',
};

export const SCENARIO_DANGER = {
  address: '서울 강서구 ○○동 ○○빌라',
  deposit: 300000000,
  area_m2: 40,

  overall_risk: {
    grade: 'D',
    score: 32,
    level: '매우 위험',
    one_line_summary:
      '솔직히 말씀드릴게요. 이 집은 위험 신호가 너무 많아요. 신탁까지 발견됐고, 전세가율도 매우 높아요. 다른 매물 알아보시는 걸 강력히 권유드려요. 🚨',
  },

  market_analysis: {
    average_market_price: 320000000,
    deposit: 300000000,
    jeonse_ratio: 0.94,
    grade: 'danger',
    conversational:
      '비슷한 집 시세가 3억 2천인데 보증금이 3억이에요. 전세가율 94%... 정부 기준 80%를 한참 넘었어요. 깡통전세 위험이 매우 높아요.',
    details: [
      '국토부 실거래가 평균: 3억 2천만 원',
      '전세가율 94% (정부 기준 80% 한참 초과)',
      '깡통전세 위험 매우 높음',
    ],
  },

  registry_analysis: {
    mortgage_max: 50000000,
    has_trust: true,
    has_seizure: false,
    grade: 'danger',
    conversational:
      "🚨 큰일이에요. 등기부에 '신탁' 표시가 있어요. 이건 진짜 위험해요. 임대인이 진짜 집주인이 아닐 수 있어요. 거기다 근저당도 5천만 원 있어요. 이 매물은 정말 피하시는 게 좋겠어요.",
    details: [
      '근저당: 5천만 원',
      '신탁: 있음 ⚠️ (소유권이 신탁회사에 있음)',
      '압류·가압류: 없음',
    ],
  },

  insurance_analysis: {
    eligible: false,
    grade: 'danger',
    conversational:
      '보증보험 가입도 어려울 것 같아요. 공시가격 대비 보증금이 너무 높아요. 안전장치도 없는 상태인 거예요.',
    details: [
      'HUG 안심전세 가입 기준 미충족',
      '공시가격 대비 보증금 비율 초과',
    ],
  },

  checklist: [
    '이 매물은 다시 생각해보세요',
    '공인중개사·법무사 상담 강력 권유',
    '다른 안전한 매물 알아보기',
  ],

  saju_unlocked: false,
  saju_lock_message:
    '위험도 D라 사주 매칭은 잠겨있어요. 우선 더 안전한 매물을 알아보세요.',
};

export const SCENARIOS = {
  safe: SCENARIO_SAFE,
  warning: SCENARIO_WARNING,
  danger: SCENARIO_DANGER,
};
