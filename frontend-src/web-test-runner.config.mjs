/** @type {import('@web/test-runner').TestRunnerConfig} */
export default {
  files: "test/**/*.test.js",
  nodeResolve: true,
  // Generous timeout for CI environments
  testsFinishTimeout: 60000,
};
