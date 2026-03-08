exports.getIndex = (req, res) => {
  const config = {
    nodeEnv: process.env.NODE_ENV || 'development',
    hasDatabaseUrl: !!process.env.DATABASE_URL,
    hasApiKey: !!process.env.API_KEY
  };
  
  res.json({
    message: 'Welcome to POC1 App',
    environment: config.nodeEnv,
    timestamp: new Date().toISOString()
  });
};
