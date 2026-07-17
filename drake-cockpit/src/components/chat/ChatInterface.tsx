'use client';

import React, { useState, useCallback } from 'react';

type Message = {
  sender: 'operator' | 'agent';
  text: string;
};

interface ChatInterfaceProps {
  agent: 'PO' | 'EL' | 'RM' | 'Steward';
}

export function ChatInterface({ agent }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(async () => {
    if (!input.trim()) return;
    const newMessage: Message = { sender: 'operator', text: input };
    setMessages((prev) => [...prev, newMessage]);
    setInput('');
    setLoading(true);
    try {
      const res = await fetch(`/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent, message: input }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { sender: 'agent', text: data.reply }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: 'agent', text: 'Error: could not reach agent.' },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, agent]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      <div className="p-4 border-b font-semibold">Chat with {agent}</div>
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm">No messages yet. Start a conversation.</p>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`p-2 rounded-lg max-w-[80%] ${
              msg.sender === 'operator'
                ? 'bg-blue-100 self-end ml-auto'
                : 'bg-gray-100 self-start'
            }`}
          >
            <span className="text-xs font-semibold">
              {msg.sender === 'operator' ? 'You' : agent}
            </span>
            <p className="text-sm mt-1">{msg.text}</p>
          </div>
        ))}
      </div>
      <div className="p-4 border-t flex items-center gap-2">
        <input
          type="text"
          placeholder="Type a message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 border rounded px-3 py-2 text-sm"
          disabled={loading}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
