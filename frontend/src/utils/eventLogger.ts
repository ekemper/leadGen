import { api } from '../config/api';

// Helper to send event to backend
async function sendEvent({ source, tag, data, type }: { source: 'browser'; tag: string; data: any; type: 'error' | 'message' | 'log'; }) {
  try {
    // Commented out event logging
    // await api.post('/api/events', {
    //   source,
    //   tag,
    //   data,
    //   type,
    // });
  } catch (err) {
    // Optionally, fallback to local logging if API fails
    // console.warn('Failed to send event:', err);
  }
}

function isEventApiUrl(url: string) {
  try {
    const u = new URL(url, window.location.origin);
    return u.pathname.startsWith('/api/events');
  } catch {
    return false;
  }
}

// Patch console methods
const originalLog = console.log;
const originalError = console.error;

console.log = function (...args) {
  // Commented out event logging
  // sendEvent({ source: 'browser', tag: 'console.log', data: { args }, type: 'log' });
  originalLog.apply(console, args);
};

console.error = function (...args) {
  // Commented out event logging
  // sendEvent({ source: 'browser', tag: 'console.error', data: { args }, type: 'error' });
  originalError.apply(console, args);
};

// Listen for uncaught errors
window.addEventListener('error', function (event) {
  // Commented out event logging
  // sendEvent({
  //   source: 'browser',
  //   tag: 'window.onerror',
  //   data: {
  //     message: event.message,
  //     filename: event.filename,
  //     lineno: event.lineno,
  //     colno: event.colno,
  //     error: event.error ? event.error.stack || String(event.error) : null,
  //   },
  //   type: 'error',
  // });
});

// Listen for unhandled promise rejections
window.addEventListener('unhandledrejection', function (event) {
  // Commented out event logging
  // sendEvent({
  //   source: 'browser',
  //   tag: 'unhandledrejection',
  //   data: {
  //     reason: event.reason ? (event.reason.stack || String(event.reason)) : null,
  //   },
  //   type: 'error',
  // });
});

// --- Network request logging ---
// Patch fetch
const originalFetch = window.fetch;
window.fetch = function(input: RequestInfo | URL, init?: RequestInit) {
  const method = (init && init.method) || 'GET';
  const url = typeof input === 'string' ? input : (input instanceof URL ? input.toString() : input.url);
  if (isEventApiUrl(url)) {
    return originalFetch.apply(this, [input, init]);
  }
  const start = performance.now();
  return originalFetch.apply(this, [input, init]).then(
    (response) => {
      const duration = performance.now() - start;
      // Commented out event logging
      // sendEvent({
      //   source: 'browser',
      //   tag: 'network',
      //   data: {
      //     method,
      //     url,
      //     status: response.status,
      //     ok: response.ok,
      //     duration,
      //   },
      //   type: response.ok ? 'log' : 'error',
      // });
      return response;
    },
    (error) => {
      const duration = performance.now() - start;
      // Commented out event logging
      // sendEvent({
      //   source: 'browser',
      //   tag: 'network',
      //   data: {
      //     method,
      //     url,
      //     status: null,
      //     ok: false,
      //     duration,
      //     error: error?.message || String(error),
      //   },
      //   type: 'error',
      // });
      throw error;
    }
  );
};

// Patch XMLHttpRequest
const OriginalXMLHttpRequest = window.XMLHttpRequest;
function PatchedXMLHttpRequest(this: XMLHttpRequest) {
  const xhr = new OriginalXMLHttpRequest();
  let method = '';
  let url = '';
  let start = 0;

  const open = xhr.open;
  xhr.open = function(_method: string, _url: string | URL, async?: boolean, username?: string | null, password?: string | null) {
    method = _method;
    url = typeof _url === 'string' ? _url : _url.toString();
    // @ts-ignore
    return open.apply(xhr, arguments);
  };

  const send = xhr.send;
  xhr.send = function(body?: Document | XMLHttpRequestBodyInit | null) {
    start = performance.now();
    xhr.addEventListener('loadend', function() {
      if (isEventApiUrl(url)) return;
      const duration = performance.now() - start;
      // Commented out event logging
      // sendEvent({
      //   source: 'browser',
      //   tag: 'network',
      //   data: {
      //     method,
      //     url,
      //     status: xhr.status,
      //     ok: xhr.status >= 200 && xhr.status < 400,
      //     duration,
      //   },
      //   type: xhr.status >= 200 && xhr.status < 400 ? 'log' : 'error',
      // });
    });
    // @ts-ignore
    return send.apply(xhr, arguments);
  };

  return xhr;
}
window.XMLHttpRequest = PatchedXMLHttpRequest as any;

export {}; 