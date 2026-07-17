import { render, screen } from '@testing-library/react';
import RootLayout from '@/app/layout';
import { vi } from 'vitest';

// Mock Next.js font
vi.mock('next/font/google', () => ({
  Inter: () => ({ className: 'mock-inter' }),
}));

// Mock sidebar
vi.mock('@/components/sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

// Mock providers
vi.mock('@/app/providers', () => ({
  Providers: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('RootLayout', () => {
  it('renders sidebar and children', () => {
    render(
      <RootLayout>
        <div data-testid="content">Hello</div>
      </RootLayout>
    );
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('content')).toBeInTheDocument();
  });
});
