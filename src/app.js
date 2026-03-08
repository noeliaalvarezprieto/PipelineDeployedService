const express = require('express');
const healthRoutes = require('./routes/health');
const indexRoutes = require('./routes/index');

const app = express();

app.use(express.json());

// Routes
app.use('/health', healthRoutes);
app.use('/', indexRoutes);

module.exports = app;
