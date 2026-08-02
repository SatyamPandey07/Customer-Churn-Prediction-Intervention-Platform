const express = require('express');
const { Server } = require('socket.io');

const app = express();
const server = app.listen(3001, () => {
    console.log('Realtime Gateway listening on port 3001');
});
const io = new Server(server, { cors: { origin: '*' } });

io.on('connection', (socket) => {
    console.log('client connected:', socket.id);
});
