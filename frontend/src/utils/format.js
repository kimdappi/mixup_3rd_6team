export function formatDeposit(amount) {
  if (!amount && amount !== 0) return '';
  const num = Number(amount);
  if (Number.isNaN(num) || num <= 0) return '';

  const eok = Math.floor(num / 100000000);
  const man = Math.floor((num % 100000000) / 10000);

  let result = '';
  if (eok > 0) result += `${eok}억 `;
  if (man > 0) {
    const cheon = Math.floor(man / 1000);
    const baek = man % 1000;
    if (cheon > 0) result += `${cheon}천`;
    if (baek > 0) result += `${baek}`;
    result += '만원';
  } else if (eok > 0) {
    result += '원';
  }
  return result.trim();
}

export function formatNumber(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(String(value).replace(/[^\d]/g, ''));
  if (Number.isNaN(n)) return '';
  return n.toLocaleString('ko-KR');
}

export function parseNumber(value) {
  if (typeof value === 'number') return value;
  const n = Number(String(value || '').replace(/[^\d]/g, ''));
  return Number.isNaN(n) ? 0 : n;
}
