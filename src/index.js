// Main router - registers all application routes
const app = require('./app');

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT} in ${process.env.NODE_ENV || 'development'} mode | v1.0.1`);
});

// Graceful shutdown for ECS task draining
process.on('SIGTERM', () => {
  console.log('SIGTERM received, starting graceful shutdown');
  server.close(() => {
    console.log('Server closed, exiting process');
    process.exit(0);
  });
});

module.exports = server;
// zero-downtime deployment test - 28 March 2026
