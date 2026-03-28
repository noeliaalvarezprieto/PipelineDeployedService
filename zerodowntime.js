import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const errors = new Counter('deployment_errors');

export const options = {
  vus: 10,
  duration: '5m',
};

const AWS_URL   = 'http://poc1-app-prod-alb-1555242999.eu-west-1.elb.amazonaws.com';
const AZURE_URL = 'https://poc2-app-prod.politeflower-fd6bb99f.francecentral.azurecontainerapps.io';

export default function () {
  const target = __ENV.TARGET === 'azure' ? AZURE_URL : AWS_URL;
  const res = http.get(`${target}/health`);
  
  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
  });
  
  if (!ok) errors.add(1);
  sleep(0.5);
}
