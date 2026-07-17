// This test will fail initially because the ChatInterface component does not exist yet.
// Run: npm test -- ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '../ChatInterface';

describe('ChatInterface', () => {
  it('renders an empty message list and input field', () => {
    render(<ChatInterface agent="PO" />);
    expect(screen.getByPlaceholderText(/Type a message/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    expect(screen.queryByRole('listitem')).toBeNull();
  });

  it('allows typing and sending a message', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ reply: 'Hello, Operator' }),
      })
    ) as jest.Mock;

    render(<ChatInterface agent="PO" />);
    const input = screen.getByPlaceholderText(/Type a message/);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
      expect(screen.getByText('Hello, Operator')).toBeInTheDocument();
    });

    (global.fetch as jest.Mock).mockClear();
  });
});
