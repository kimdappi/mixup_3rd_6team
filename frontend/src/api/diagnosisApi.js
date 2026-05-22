const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 전세계약 빠른 진단 (JSON 요청)
 * @param {Object} params
 * @param {string} params.address         - 전체 주소 (예: "서울 강서구 가양동 강변아파트")
 * @param {number} params.area_sqm        - 전용면적 (㎡, 예: 59.5)
 * @param {number} params.user_deposit    - 보증금 (원, 예: 300000000)
 * @param {string} [params.housing_type]  - 주택 유형 (기본: "apartment")
 * @param {string} [params.contract_stage]- 계약 단계 (기본: "before_contract")
 */
export async function quickDiagnosis({
  address,
  area_sqm,
  user_deposit,
  housing_type = 'apartment',
  contract_stage = 'before_contract',
}) {
  const res = await fetch(`${BASE}/diagnoses/quick`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address, area_sqm, user_deposit, housing_type, contract_stage }),
  });
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail || ''; } catch { /* ignore */ }
    throw new Error(`진단 API 오류: ${res.status}${detail ? ` - ${detail}` : ''}`);
  }
  return await res.json();
}

/**
 * 전세계약 전체 진단 (문서 업로드 포함, multipart/form-data)
 * @param {Object} params
 * @param {string} params.address
 * @param {number} params.area_sqm
 * @param {number} params.user_deposit
 * @param {string} [params.housing_type]
 * @param {string} [params.contract_stage]
 * @param {File|null} [params.registryDocument]       - 등기부등본 파일
 * @param {File|null} [params.buildingLedgerDocument] - 건축물대장 파일
 * @param {File|null} [params.draftContractDocument]  - 계약서 초안 파일
 */
export async function fullDiagnosis({
  address,
  area_sqm,
  user_deposit,
  housing_type = 'apartment',
  contract_stage = 'before_contract',
  registryDocument = null,
  buildingLedgerDocument = null,
  draftContractDocument = null,
}) {
  const formData = new FormData();
  formData.append('address', address);
  formData.append('area_sqm', String(area_sqm));
  formData.append('user_deposit', String(user_deposit));
  formData.append('housing_type', housing_type);
  formData.append('contract_stage', contract_stage);
  if (registryDocument) formData.append('registry_document', registryDocument);
  if (buildingLedgerDocument) formData.append('building_ledger_document', buildingLedgerDocument);
  if (draftContractDocument) formData.append('draft_contract_document', draftContractDocument);

  const res = await fetch(`${BASE}/diagnoses/full`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail || ''; } catch { /* ignore */ }
    throw new Error(`진단 API 오류: ${res.status}${detail ? ` - ${detail}` : ''}`);
  }
  return await res.json();
}
