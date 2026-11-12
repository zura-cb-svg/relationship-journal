// The browser and API share an origin. Access tokens never enter persistent storage.
let accessToken = null;
let refreshPromise = null;
let generation = 0;
export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const lock = (fn) => navigator.locks ? navigator.locks.request('between-auth-session', fn) : fn();
async function send(path, opts = {}, token = null) {
  const headers = new Headers(opts.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let body = opts.body;
  if (body !== undefined && !(body instanceof URLSearchParams)) {
    headers.set('Content-Type', 'application/json'); body = JSON.stringify(body);
  }
  let response;
  try { response = await fetch(path, {...opts, headers, body, credentials: 'same-origin', cache: 'no-store'}); }
  catch { throw new ApiError(0, 'Cannot reach your journal. Check that the API is running.'); }
  const isJson = response.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;
  if (!response.ok || !isJson) {
    const detail = data?.detail;
    const message = response.status === 429 ? `Too many requests. Try again in ${response.headers.get('Retry-After') || 'a few'} seconds.` :
      Array.isArray(detail) ? 'Check the highlighted requirements and try again.' :
      typeof detail === 'string' ? detail : !isJson ? 'The API is not available at this address.' : 'Something went wrong. Please try again.';
    throw new ApiError(response.status, message);
  }
  return data;
}
export function forget() { generation++; accessToken = null; }
export function hasToken() { return Boolean(accessToken); }
export function refresh() {
  if (!refreshPromise) {
    const current = generation;
    refreshPromise = lock(async () => {
      if (current !== generation) throw new ApiError(401, 'Session ended.');
      const result = await send('/refresh', {method:'POST'});
      if (current !== generation) throw new ApiError(401, 'Session ended.');
      accessToken = result.access_token; return result;
    }).catch(error => { if (current === generation) accessToken = null; throw error; }).finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}
export async function login(email, password) {
  return lock(async () => {
    const data = await send('/login', {method:'POST', body:new URLSearchParams({username:email,password})});
    generation++; accessToken = data.access_token; return data;
  });
}
export function signup(body) { return send('/signup', {method:'POST',body}); }
export async function logout() { return lock(async () => { await send('/logout',{method:'POST'}); forget(); }); }
export async function api(path, options = {}) {
  const token = accessToken;
  if (!token) await refresh();
  const used = accessToken;
  try { return await send(path,options,used); }
  catch (error) {
    if (error.status !== 401 || !accessToken) throw error;
    if (accessToken === used) await refresh();
    return send(path,options,accessToken);
  }
}
export function query(path, values) {
  const q = new URLSearchParams();
  for (const [key,value] of Object.entries(values)) if (value !== '' && value != null) q.set(key,String(value));
  return `${path}?${q}`;
}
