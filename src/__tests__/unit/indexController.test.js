const indexController = require('../../controllers/indexController');

describe('Index Controller', () => {
  test('getIndex returns welcome message', () => {
    const req = {};
    const res = {
      json: jest.fn()
    };

    indexController.getIndex(req, res);

    expect(res.json).toHaveBeenCalled();
    const response = res.json.mock.calls[0][0];
    expect(response).toHaveProperty('message');
    expect(response).toHaveProperty('environment');
    expect(response).toHaveProperty('timestamp');
  });
});
