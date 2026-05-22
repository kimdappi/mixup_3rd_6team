import { SCENARIOS } from '../data/scenarios.js';
import { sleep } from '../utils/delay.js';

// 안전성 분석(매물 위험도)은 백엔드 미구현 영역이라 mock 유지.
// 사주 매칭(mockSajuMatch)은 실제 백엔드(`/api/saju`)로 일원화돼서 제거됨.
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
