const request = require('supertest');

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

describe('GET /health', () => {
  test('should return 200 and healthy status', async () => {
    const response = await request(BASE_URL).get('/health');
    
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'healthy' });
  });
});
