/* eslint-disable */
/**
 * WebSocket Connection Test for French Novel Tool
 * 
 * Open this file in your browser's console to test WebSocket connection
 * and Socket.IO event reception.
 * 
 * Usage:
 * 1. Open browser DevTools (F12)
 * 2. Copy and paste this entire file into the console
 * 3. Call: testWebSocket(jobId, token)
 * 
 * Example:
 *   testWebSocket(73, 'your-jwt-token-here')
 */

function testWebSocket(jobId, token) {
  console.log('='.repeat(60));
  console.log('WebSocket Connection Test for Job', jobId);
  console.log('='.repeat(60));
  
  // Check if socket.io-client is loaded
  if (typeof io === 'undefined') {
    console.error('❌ Socket.IO client not loaded. Loading from CDN...');
    const script = document.createElement('script');
    script.src = 'https://cdn.socket.io/4.5.4/socket.io.min.js';
    script.onload = () => {
      console.log('✅ Socket.IO client loaded');
      testWebSocket(jobId, token);
    };
    document.head.appendChild(script);
    return;
  }
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
  console.log('API URL:', apiUrl);
  
  // Create Socket.IO connection
  const socket = io(apiUrl, {
    path: '/socket.io/',
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    query: {
      token: token,
    },
  });
  
  console.log('Socket.IO connection created');
  
  // Connection events
  socket.on('connect', () => {
    console.log('✅ Connected to WebSocket server');
    console.log('Socket ID:', socket.id);
    
    // Join job room
    console.log(`Joining job room for job ${jobId}...`);
    socket.emit('join_job', { job_id: jobId, token: token });
  });
  
  socket.on('disconnect', (reason) => {
    console.log('❌ Disconnected from WebSocket server');
    console.log('Reason:', reason);
  });
  
  socket.on('connect_error', (err) => {
    console.error('❌ Connection error:', err.message);
  });
  
  socket.on('error', (data) => {
    console.error('❌ Socket.IO error:', data);
  });
  
  // Room events
  socket.on('joined_room', () => {
    console.log('✅ Successfully joined job room');
  });
  
  socket.on('left_room', () => {
    console.log('⚠️  Left job room');
  });
  
  // Job progress events
  socket.on('job_progress', (data) => {
    console.log('📊 Job progress update received:');
    console.log('  Status:', data.status);
    console.log('  Progress:', data.progress_percent + '%');
    console.log('  Current step:', data.current_step);
    console.log('  Processed chunks:', data.processed_chunks + '/' + data.total_chunks);
    console.log('  Full data:', data);
  });
  
  console.log('\n⏳ Waiting for events... (this will run for 60 seconds)');
  console.log('To manually disconnect, call: socket.disconnect()');
  
  // Store socket globally for manual control
  window.testSocket = socket;
  
  // Auto-disconnect after 60 seconds
  setTimeout(() => {
    console.log('\n⏱️  60 seconds elapsed, disconnecting...');
    socket.disconnect();
    console.log('Test complete. To run again, call: testWebSocket(jobId, token)');
  }, 60000);
  
  return socket;
}

// Helper to get token from localStorage (if using the actual app)
function getStoredToken() {
  const authData = localStorage.getItem('auth');
  if (authData) {
    try {
      const parsed = JSON.parse(authData);
      return parsed.state?.accessToken;
    } catch (e) {
      console.error('Failed to parse auth data:', e);
    }
  }
  return null;
}

console.log('WebSocket test script loaded!');
console.log('\nTo test:');
console.log('  testWebSocket(jobId, token)');
console.log('\nTo get stored token:');
console.log('  getStoredToken()');
console.log('\nExample:');
console.log('  testWebSocket(73, getStoredToken())');
