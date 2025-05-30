import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CacheProvider } from '@emotion/react';
import createCache from '@emotion/cache';
import { SnackbarProvider } from 'notistack';
import AppLayout from './components/Layout/AppLayout';
import { MemoryRouter } from 'react-router-dom';

const emotionCache = createCache({ key: 'css', prepend: true });

// Mock prompt and fetch before tests
beforeAll(() => {
  window.prompt = jest.fn(() => 'smartgrantfinder');
  global.fetch = jest.fn().mockResolvedValue({ ok: true });
});
beforeEach(() => {
  localStorage.setItem('authOK', '1');
});

test('renders Dashboard menu item in AppLayout', async () => {
  render(
    <CacheProvider value={emotionCache}>
      <SnackbarProvider>
        <MemoryRouter initialEntries={['/']}>
          <AppLayout />
        </MemoryRouter>
      </SnackbarProvider>
    </CacheProvider>
  );
  const dashboardLink = await screen.findByText(/Dashboard/i);
  expect(dashboardLink).toBeInTheDocument();
});
