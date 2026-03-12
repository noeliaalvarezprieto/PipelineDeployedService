const request = require('supertest');
const app = require('../../app');  // Importar la app, no el servidor

describe('GET /', () => {
  test('should return welcome message', async () => {
    const response = await request(app).get('/');

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message');
    expect(response.body).toHaveProperty('environment');
    expect(response.body).toHaveProperty('timestamp');
  });
});