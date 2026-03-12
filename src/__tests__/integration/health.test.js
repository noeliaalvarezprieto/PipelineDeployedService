const request = require('supertest');
const app = require('../../app');  // Importar la app, no el servidor

describe('GET /health', () => {
  test('should return 200 and healthy status', async () => {
    const response = await request(app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'healthy' });
  });
});