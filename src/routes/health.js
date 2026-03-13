// Health check route — used by ALB and ECS health checks
const express = require('express');
const router = express.Router();
const healthController = require('../controllers/healthController');

router.get('/', healthController.getHealth);

module.exports = router;
