const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function realSajuMatch(birthInfo, address) {
  const res = await fetch(`${BASE}/api/saju`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: birthInfo.name,
      year: birthInfo.year,
      month: birthInfo.month,
      day: birthInfo.day,
      hour: birthInfo.hour,
      minute: birthInfo.minute,
      city: birthInfo.city,
      address,
    }),
  });
  if (!res.ok) {
    let detail = '';
    try {
      detail = (await res.json()).detail || '';
    } catch {
      // ignore parse error
    }
    throw new Error(`API error: ${res.status}${detail ? ` - ${detail}` : ''}`);
  }
  return await res.json();
}
