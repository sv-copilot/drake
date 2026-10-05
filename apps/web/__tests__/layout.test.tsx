import { render, screen } from '@testing-library/react';
import RootLayout from '@/app/layout';
import { describe, expect, it, vi } from 'vitest';

// Mock Next.js font
vi.mock('next/font/google', () => ({
  Inter: () => ({ className: 'mock-inter' }),
}));

// Mock the app shell (a client component with its own nav tests)
vi.mock('@/components/app-shell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}));

// Mock providers
vi.mock('@/app/providers', () => ({
  Providers: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('RootLayout', () => {
  it('renders the app shell and children', () => {
    render(
      <RootLayout>
        <div data-testid="content">Hello</div>
      </RootLayout>
    );
    expect(screen.getByTestId('app-shell')).toBeInTheDocument();
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });
});
