import React, { useEffect, useState } from 'react';
import axios from 'axios';

function History() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get('http://localhost:3000/history');
        setHistory(response.data);
      } catch (error) {
        console.error('Error fetching history', error);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div>
      <h2>Game History</h2>
      <ul>
        {history.map((room, index) => (
          <li key={index}>
            Room ID: {room.room_id}, Players: {room.current_players}/{room.max_players}, Bet: {room.total_bet_amount}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default History;
