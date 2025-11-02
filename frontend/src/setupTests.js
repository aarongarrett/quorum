// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers } from './__mocks__/handlers';

// Set environment variables for tests
process.env.VITE_API_URL = 'http://localhost';

// Suppress all warnings during tests for cleaner output
// Only actual errors will be shown
const originalWarn = console.warn;
const originalError = console.error;

beforeAll(() => {
  // Suppress all console.warn
  console.warn = () => {};

  // Suppress console.error for warnings (but keep real errors)
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning:') ||
       args[0].includes('inside a test was not wrapped in act'))
    ) {
      return; // Suppress warnings
    }
    originalError.call(console, ...args); // Keep real errors
  };
});

afterAll(() => {
  console.warn = originalWarn;
  console.error = originalError;
});

// Mock localStorage with actual storage functionality
const localStorageMock = (() => {
  let store = {};

  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    })
  };
})();

global.localStorage = localStorageMock;

// Clear localStorage before each test
beforeEach(() => {
  localStorage.clear();
});

// Mock EventSource for SSE tests
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.onmessage = null;
    this.onerror = null;
    this.readyState = 1; // OPEN
  }

  close() {
    this.readyState = 2; // CLOSED
  }
}

global.EventSource = MockEventSource;

// Mock HTMLCanvasElement for QR code rendering in tests
// jsdom doesn't support canvas, so we mock getContext to prevent errors
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
  fillRect: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn(),
  putImageData: jest.fn(),
  createImageData: jest.fn(),
  setTransform: jest.fn(),
  drawImage: jest.fn(),
  save: jest.fn(),
  fillText: jest.fn(),
  restore: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  closePath: jest.fn(),
  stroke: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
  rotate: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  measureText: jest.fn(() => ({ width: 0 })),
  transform: jest.fn(),
  rect: jest.fn(),
  clip: jest.fn(),
}));

// Set up MSW mock server for API calls
export const server = setupServer(...handlers);

// Start server before all tests
beforeAll(() => server.listen());

// Reset handlers after each test
afterEach(() => server.resetHandlers());

// Clean up after all tests
afterAll(() => server.close());
