import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom'; // 导入Routes和Route

import CreateRoom from './CreateRoom';
import JoinRoom from './JoinRoom';
import History from './History';

function App() {
  return (
    <Router>
      <div>
        <Routes> {/* 用Routes替换Switch */}
          <Route path="/create-room" element={<CreateRoom />} />
          <Route path="/join-room" element={<JoinRoom />} />
          <Route path="/history" element={<History />} />
          <Route path="/" element={
            <div>
              <h1>Welcome to the Dice Game</h1>
              <a href="/create-room">Create Room</a><br/>
              <a href="/join-room">Join Room</a><br/>
              <a href="/history">Game History</a>
            </div>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
