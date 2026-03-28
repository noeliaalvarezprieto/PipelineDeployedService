import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '60s', target: 30 },
    { duration: '60s', target: 50 },
    { duration: '30s', target: 0  },
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed:   ['rate<0.05'],
  },
};

const AWS_URL   = 'http://poc1-app-prod-alb-1555242999.eu-west-1.elb.amazonaws.com';
const AZURE_URL = 'https://poc2-app-prod.politeflower-fd6bb99f.francecentral.azurecontainerapps.io';

export default function () {
  const target = __ENV.TARGET === 'azure' ? AZURE_URL : AWS_URL;
  const res = http.get(`${target}/health`);
  check(res, {
    'status is 200':          (r) => r.status === 200,
    'response time < 3000ms': (r) => r.timings.duration < 3000,
  });
  sleep(1);
}
