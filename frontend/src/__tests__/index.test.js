import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '../App';

// Mock ReactDOM.createRoot
jest.mock('react-dom/client', () => ({
  createRoot: jest.fn()
}));

// Mock App component
jest.mock('../App', () => {
  return jest.fn(() => <div>Mocked App</div>);
});

describe('index', () => {
  let mockRoot;
  let mockRender;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

    // Create mock render function
    mockRender = jest.fn();

    // Create mock root object
    mockRoot = {
      render: mockRender
    };

    // Mock createRoot to return our mock root
    ReactDOM.createRoot.mockReturnValue(mockRoot);

    // Mock getElementById
    document.getElementById = jest.fn((id) => {
      if (id === 'root') {
        return document.createElement('div');
      }
      return null;
    });
  });

  it('should create root with the root element', () => {
    // Require index to execute the code
    jest.isolateModules(() => {
      require('../index');
    });

    expect(document.getElementById).toHaveBeenCalledWith('root');
    expect(ReactDOM.createRoot).toHaveBeenCalledWith(expect.any(HTMLElement));
  });

  it('should render App inside React.StrictMode', () => {
    jest.isolateModules(() => {
      require('../index');
    });

    expect(mockRender).toHaveBeenCalledTimes(1);

    // Get the rendered element
    const renderedElement = mockRender.mock.calls[0][0];

    // Check that it's a StrictMode component
    expect(renderedElement.type).toBe(React.StrictMode);

    // Check that App is a child of StrictMode
    expect(renderedElement.props.children.type).toBe(App);
  });

  it('should call render on the created root', () => {
    jest.isolateModules(() => {
      require('../index');
    });

    expect(mockRender).toHaveBeenCalled();
  });
});
