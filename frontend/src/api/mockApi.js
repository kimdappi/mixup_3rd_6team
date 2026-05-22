import { SCENARIOS } from '../data/scenarios.js';
import { sleep } from '../utils/delay.js';

export async function mockAnalyze(input) {
  await sleep(200);

  if (input?.scenarioType && SCENARIOS[input.scenarioType]) {
    return { ...SCENARIOS[input.scenarioType] };
  }

  const deposit = Number(input?.deposit) || 0;
  const ratio = deposit / 350000000;
  if (ratio < 0.7) return { ...SCENARIOS.safe, address: input?.address || SCENARIOS.safe.address };
  if (ratio < 0.9) return { ...SCENARIOS.warning, address: input?.address || SCENARIOS.warning.address };
  return { ...SCENARIOS.danger, address: input?.address || SCENARIOS.danger.address };
}

const MONTH_LACK_MAP = {
  1: ['水'],
  2: ['水'],
  3: ['水', '金'],
  4: ['火'],
  5: ['火'],
  6: ['火'],
  7: ['土'],
  8: ['土'],
  9: ['金'],
  10: ['金'],
  11: ['木'],
  12: ['木', '水'],
};

export async function mockSajuMatch(birthInfo) {
  await sleep(800);

  const month = Number(birthInfo?.month) || 6;
  const lacking = MONTH_LACK_MAP[month] || ['水'];

  const distribution = { 木: 2, 火: 2, 土: 2, 金: 1, 水: 1 };
  lacking.forEach((key) => {
    if (distribution[key] > 0) distribution[key] -= 1;
  });

  const matchDetails = [
    { factor: '한강 인접 (水 보완)', points: 30 },
    { factor: '남향 가능성 (火 보완)', points: 15 },
    { factor: '5호선 인접 (활기, 火)', points: 10 },
    { factor: '서향 요소 부족 (金)', points: -7 },
  ];
  const matchScore = matchDetails.reduce((acc, d) => acc + d.points, 50);

  return {
    saju_pillars: '戊寅年 己未月 甲戌日 壬申時',
    oheng_distribution: distribution,
    lacking_oheng: lacking,
    match_score: matchScore,
    match_grade: matchScore >= 80 ? '아주 좋음' : matchScore >= 65 ? '양호' : '보통',
    match_details: matchDetails,
    conversational:
      lacking.includes('水')
        ? '지원님은 물(水) 기운이 부족한 사주신데, 이 집은 한강에서 도보 8분 거리예요! 부족한 기운을 자연스럽게 채워줄 수 있는 좋은 환경이에요. 👍'
        : '지원님 사주와 이 집은 전반적으로 잘 어울리는 흐름이에요. 채광과 동선이 부족한 기운을 보완해주는 구성이라, 살면서 편안함을 느끼기 좋아요. 👍',
    disclaimer: '사주는 전통 문화 콘텐츠로 제공됩니다. 계약 결정은 안전성 분석을 우선해주세요.',
  };
}
