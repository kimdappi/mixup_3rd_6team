const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * POST /api/registry/analyze
 * multipart/form-data: file (PDF) + user_deposit_won (원 단위 정수)
 */
export async function analyzeRegistry({ file, userDepositWon }) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('user_deposit_won', String(userDepositWon));

  const res = await fetch(`${BASE}/api/registry/analyze`, {
    method: 'POST',
    body: fd,
  });

  if (!res.ok) {
    let detail = '';
    try {
      detail = (await res.json()).detail || '';
    } catch {
      // ignore
    }
    const err = new Error(
      `등기부 분석 API 오류 (${res.status})${detail ? ` - ${detail}` : ''}`
    );
    err.status = res.status;
    err.detail = detail;
    throw err;
  }

  return await res.json();
}
