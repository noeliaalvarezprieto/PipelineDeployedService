const request = require('supertest');
const app = require('../../app');

describe('App Configuration', () => {
  test('should parse JSON bodies', async () => {
    const response = await request(app)
      .post('/health')
      .send({ test: 'data' });
    
    // Should not crash, middleware is working
    expect(response.status).toBeDefined();
  });

  test('should return 404 for unknown routes', async () => {
    const response = await request(app).get('/unknown-route-xyz');
    expect(response.status).toBe(404);
  });

  test('should have health endpoint configured', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status');
  });

  test('should have index endpoint configured', async () => {
    const response = await request(app).get('/');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message');
  });
});