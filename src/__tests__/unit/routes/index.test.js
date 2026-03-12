const request = require('supertest');
const express = require('express');
const indexRoutes = require('../../../routes/index');

const app = express();
app.use('/', indexRoutes);

describe('Index Routes', () => {
  test('GET / should return welcome message with environment and timestamp', async () => {
    const response = await request(app).get('/');
    
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message');
    expect(response.body).toHaveProperty('environment');
    expect(response.body).toHaveProperty('timestamp');
  });
});