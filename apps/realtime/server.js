const express = require('express');
const { Server } = require('socket.io');
const { createClient } = require('redis');
const winston = require('winston');
const client = require('prom-client');
const { trace } = require('@opentelemetry/api');

// Setup structured logging
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [new winston.transports.Console()]
});

// Setup Prometheus metrics
const collectDefaultMetrics = client.collectDefaultMetrics;
collectDefaultMetrics({ prefix: 'realtime_' });


const app = express();

app.get('/metrics', async (req, res) => {
    res.set('Content-Type', client.register.contentType);
    res.send(await client.register.metrics());
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/live', (req, res) => res.json({ status: 'alive' }));
app.get('/ready', (req, res) => res.json({ status: 'ready' }));

const server = app.listen(3001, () => {
    logger.info('Realtime Gateway listening on port 3001');
});
const io = new Server(server, { cors: { origin: '*' } });

io.on('connection', (socket) => {
    logger.info(`client connected: ${socket.id}`);
});

async function startRedis() {
    const redisClient = createClient({ url: process.env.REDIS_URL || 'redis://localhost:6379/0' });
    redisClient.on('error', (err) => logger.error('Redis Client Error', { error: err.message }));
    await redisClient.connect();

    logger.info('Connected to Redis, subscribing to churn_updates...');
    await redisClient.subscribe('churn_updates', (message) => {
        const tracer = trace.getTracer('realtime');
        tracer.startActiveSpan('broadcast_churn_update', (span) => {
            try {
                const data = JSON.parse(message);
                logger.info('Broadcasting churn_update', { payload: data });
                io.emit('churn_update', data);
            } catch (e) {
                logger.error('Error parsing redis message', { error: e.message });
            } finally {
                span.end();
            }
        });
    });
}

startRedis().catch(err => logger.error('Startup Error', { error: err.message }));
