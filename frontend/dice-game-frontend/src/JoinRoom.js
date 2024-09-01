import React, { useState } from 'react';
import axios from 'axios';

function JoinRoom() {
  const [roomId, setRoomId] = useState('');

  const handleChange = (e) => {
    setRoomId(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('http://localhost:3000/join_room', { room_id: roomId }); // 移除response变量
      alert('Joined room successfully');
    } catch (error) {
      alert('Error joining room');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>Room ID:</label>
      <input type="text" name="room_id" onChange={handleChange} required />
      <button type="submit">Join Room</button>
    </form>
  );
}

export default JoinRoom;
