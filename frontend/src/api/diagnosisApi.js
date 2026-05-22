const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * POST /api/diagnoses/quick
 *
 * @param {Object} payload
 * @param {string} payload.address
 * @param {number} payload.user_deposit  보증금 (원 단위)
 * @param {number} payload.area_sqm      전용면적 (제곱미터)
 * @param {'apt'|'villa'|'officetel'} [payload.housing_type]
 * @param {string} [payload.contract_stage]
 */
export async function quickDiagnosis(payload) {
  const res = await fetch(`${BASE}/api/diagnoses/quick`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      address: payload.address,
      user_deposit: payload.user_deposit,
      area_sqm: payload.area_sqm,
      housing_type: payload.housing_type || 'apt',
      contract_stage: payload.contract_stage || null,
    }),
  });

  if (!res.ok) {
    let detail = '';
    try {
      detail = (await res.json()).detail || '';
    } catch {
      // ignore parse error
    }
    const err = new Error(
      `시세 진단 API 오류 (${res.status})${detail ? ` - ${detail}` : ''}`
    );
    err.status = res.status;
    err.detail = detail;
    throw err;
  }

  return await res.json();
}
