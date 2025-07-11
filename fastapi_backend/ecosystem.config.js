module.exports = {
  apps: [{
    name: 'trading-api',
    script: '/usr/bin/python3',
    args: '-m uvicorn main:app --host 0.0.0.0 --port 8000',
    cwd: '/opt/trading-api',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/opt/trading-api'
    },
    env_production: {
      NODE_ENV: 'production'
    },
    log_file: '/var/log/trading-api/combined.log',
    out_file: '/var/log/trading-api/out.log',
    error_file: '/var/log/trading-api/error.log',
    time: true
  }]
};
