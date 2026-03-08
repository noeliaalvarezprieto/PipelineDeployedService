const healthController = require('../../controllers/healthController');

describe('Health Controller', () => {
  test('getHealth returns status healthy', () => {
    const req = {};
    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    };

    healthController.getHealth(req, res);

    expect(res.status).toHaveBeenCalledWith(200);
    expect(res.json).toHaveBeenCalledWith({ status: 'healthy' });
  });
});
