const request = require('supertest');

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

describe('GET /', () => {
  test('should return welcome message', async () => {
    const response = await request(BASE_URL).get('/');
    
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message');
    expect(response.body).toHaveProperty('environment');
    expect(response.body).toHaveProperty('timestamp');
  });
});
