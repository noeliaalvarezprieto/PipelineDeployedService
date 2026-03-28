import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const errors = new Counter('deployment_errors');

export const options = {
  vus: 10,
  duration: '15m',
};

const AZURE_URL = 'https://poc2-app-prod.politeflower-fd6bb99f.francecentral.azurecontainerapps.io';

export default function () {
  const res = http.get(`${AZURE_URL}/health`);
  const ok = check(res, { 'status is 200': (r) => r.status === 200 });
  if (!ok) errors.add(1);
  sleep(0.5);
}
// zero-downtime deployment test - 28 March 2026
