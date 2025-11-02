module.exports = {
  testEnvironment: 'jest-fixed-jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],

  // Module resolution
  moduleNameMapper: {
    '\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  
  // Transform files
  transform: {
    '^.+\.(js|jsx)$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        ['@babel/preset-react', { runtime: 'automatic' }]
      ],
      plugins: ['babel-plugin-transform-vite-meta-env']
    }],
  },
  
  // Ignore node_modules except specific packages
  transformIgnorePatterns: [
    'node_modules/(?!(qrcode.react)/)',
  ],
  
  // Coverage
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/index.jsx',
    '!src/setupTests.js',
    '!src/**/*.test.{js,jsx}',
  ],
  
  // Coverage output - centralized in parent test-reports directory
  coverageDirectory: '../test-reports/frontend/coverage',

  // HTML Reporter - centralized in parent test-reports directory
  reporters: [
    'default',
    [
      'jest-html-reporters',
      {
        publicPath: '../test-reports/frontend/test-report',
        filename: 'index.html',
        pageTitle: 'Quorum Frontend Test Report',
        expand: true,
        openReport: false,
      },
    ],
  ],
  
  // Test match patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx}',
    '<rootDir>/src/**/*.{spec,test}.{js,jsx}',
  ],
};
