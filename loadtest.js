import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const API_KEY = __ENV.API_KEY || ''; // optional

const non200Rate = new Rate('non_200_rate');
const jsonParseFailRate = new Rate('json_parse_fail_rate');
const endpointErrors = new Counter('endpoint_errors');
const tooManyRequestsRate = new Rate('too_many_requests_rate');

const status200 = new Counter('status_200');
const status401 = new Counter('status_401');
const status404 = new Counter('status_404');
const status422 = new Counter('status_422');
const status429 = new Counter('status_429');
const status500 = new Counter('status_500');
const statusOther = new Counter('status_other');

export const options = {
  scenarios: {
    // Locust-like steady request pressure (better for concurrency validation)
    randomized_data_load: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 12), // requests per second
      timeUnit: '1s',
      duration: __ENV.DURATION || '1m',
      preAllocatedVUs: Number(__ENV.PRE_VUS || 20),
      maxVUs: Number(__ENV.MAX_VUS || 120),
      gracefulStop: __ENV.GRACEFUL_STOP || '5s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    non_200_rate: ['rate<0.05'],
    json_parse_fail_rate: ['rate<0.01'],
    too_many_requests_rate: ['rate<0.02'],
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
  },
};

function recordStatus(statusCode) {
  if (statusCode === 200) {
    status200.add(1);
    return;
  }
  if (statusCode === 401) {
    status401.add(1);
    return;
  }
  if (statusCode === 404) {
    status404.add(1);
    return;
  }
  if (statusCode === 422) {
    status422.add(1);
    return;
  }
  if (statusCode === 429) {
    status429.add(1);
    return;
  }
  if (statusCode >= 500) {
    status500.add(1);
    return;
  }
  statusOther.add(1);
}

function headers() {
  const h = { Accept: 'application/json' };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return { headers: h, timeout: '30s' };
}

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function buildRandomRequest() {
  // Weighted randomization: CRM 40%, Support 35%, Analytics 25%
  const roll = Math.random();

  if (roll < 0.4) {
    const statuses = ['active', 'inactive'];
    const page = Math.floor(Math.random() * 5) + 1;
    const pageSize = pickRandom([2, 5, 10, 20]);
    const status = pickRandom(statuses);
    return `${BASE_URL}/data/crm?page=${page}&page_size=${pageSize}&status=${status}`;
  }

  if (roll < 0.75) {
    const statuses = ['open', 'closed'];
    const page = Math.floor(Math.random() * 5) + 1;
    const pageSize = pickRandom([2, 5, 10, 20]);
    const status = pickRandom(statuses);
    return `${BASE_URL}/data/support?page=${page}&page_size=${pageSize}&status=${status}`;
  }

  const dates = [
    '2026-02-08',
    '2026-02-09',
    '2026-02-10',
    '2026-02-11',
    '2026-02-12',
    '2026-02-13',
    '2026-02-14',
  ];
  const d = pickRandom(dates);
  const page = Math.floor(Math.random() * 3) + 1;
  const pageSize = pickRandom([2, 5, 10]);
  return `${BASE_URL}/data/analytics?metric=daily_active_users&start_date=${d}&end_date=${d}&page=${page}&page_size=${pageSize}`;
}

export default function () {
  const url = buildRandomRequest();
  const res = http.get(url, headers());
  recordStatus(res.status);
  tooManyRequestsRate.add(res.status === 429);

  const ok = check(res, {
    'status 200': (r) => r.status === 200,
    'body exists': (r) => !!r.body && r.body.length > 2,
  });

  non200Rate.add(!ok);

  if (ok) {
    let parsed;
    try {
      parsed = res.json();
    } catch (_) {
      jsonParseFailRate.add(true);
      endpointErrors.add(1);
      sleep(Math.random() * 0.4);
      return;
    }

    const shapeOk = check(parsed, {
      'response has data key': (p) => p && Object.prototype.hasOwnProperty.call(p, 'data'),
      'response has metadata key': (p) => p && Object.prototype.hasOwnProperty.call(p, 'metadata'),
    });

    if (!shapeOk) endpointErrors.add(1);
    jsonParseFailRate.add(false);
  } else {
    endpointErrors.add(1);
  }

  // random think time like users
  sleep(Math.random() * 0.7);
}