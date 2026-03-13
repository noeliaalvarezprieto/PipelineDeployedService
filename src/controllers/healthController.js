// Returns current health status of the application
exports.getHealth = (req, res) => {
  res.status(200).json({ status: 'healthy' }
};
