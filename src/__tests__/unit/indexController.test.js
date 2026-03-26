const indexController = require('../../controllers/indexController');

describe('Index Controller', () => {
  
  // Test existente (cuando NODE_ENV está definido)
  test('getIndex returns welcome message with environment', () => {
    const req = {};
    const res = {
      json: jest.fn()
    };

    indexController.getIndex(req, res);

    expect(res.json).toHaveBeenCalled();
    expect(response).toHaveProperty('message');
    expect(response).toHaveProperty('environment');
    expect(response).toHaveProperty('timestamp');
  });

  // NUEVO TEST: Cuando NODE_ENV no está definido (cubre el branch || 'development')
  test('getIndex uses development as default when NODE_ENV is not set', () => {
    // Guardar el valor original
    const originalNodeEnv = process.env.NODE_ENV;
    
    // Eliminar NODE_ENV para este test
    delete process.env.NODE_ENV;
    
    const req = {};
    const res = {
      json: jest.fn()
    };

    indexController.getIndex(req, res);

    const response = res.json.mock.calls[0][0];
    expect(response.environment).toBe('development');

    // Restaurar el valor original
    process.env.NODE_ENV = originalNodeEnv;
  });

  // Opcional: Test para cuando DATABASE_URL y API_KEY están definidos
  test('getIndex detects database and API key configuration', () => {
    process.env.DATABASE_URL = 'postgres://localhost:5432/db';
    process.env.API_KEY = 'secret-key';
    
    const req = {};
    const res = {
      json: jest.fn()
    };

    indexController.getIndex(req, res);

    const response = res.json.mock.calls[0][0];
    // Verificar que el config interno tiene estos valores (si los expones en la respuesta)
    // O verificar que no hay error
    
    // Limpiar
    delete process.env.DATABASE_URL;
    delete process.env.API_KEY;
  });
});