import React, { useState } from 'react';
import axios from 'axios';

function CreateRoom() {
  const [roomDetails, setRoomDetails] = useState({
    max_players: '2',
    total_bet_amount: '100',
    room_id: `room_${Date.now()}`, // 生成唯一的房间ID
    creator: 'player1', // 这里你可以用动态的用户名代替
    status: 'waiting' // 默认状态为 "waiting"
  });

  const handleChange = (e) => {
    setRoomDetails({
      ...roomDetails,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:3000/create_room', roomDetails);
      alert(`Room created successfully with ID: ${response.data.room_id}`);
    } catch (error) {
      alert('Error creating room: ' + error.response?.data?.error || error.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>Max Players:</label>
      <select name="max_players" onChange={handleChange} value={roomDetails.max_players}>
        <option value="2">2人</option>
        <option value="5">5人</option>
        <option value="20">20人</option>
        <option value="100">100人</option>
      </select>

      <label>Bet Amount:</label>
      <select name="total_bet_amount" onChange={handleChange} value={roomDetails.total_bet_amount}>
        <option value="100">100</option>
        <option value="1000">1000</option>
        <option value="10000">10000</option>
        <option value="100000">100000</option>
      </select>

      <button type="submit">Create Room</button>
    </form>
  );
}

export default CreateRoom;
