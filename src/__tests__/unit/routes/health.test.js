const request = require('supertest');
const express = require('express');
const healthRoutes = require('../../../routes/health');

const app = express();
app.use('/health', healthRoutes);

describe('Health Routes', () => {
  test('GET /health should return 200 and status ok', async () => {
    const response = await request(app).get('/health');
    
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'healthy');
    
  });
});