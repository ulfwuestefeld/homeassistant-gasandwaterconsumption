import resolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";

export default {
  input: "src/gas-water-meter-panel.js",
  output: {
    file: "../gas-water-meter/custom_components/gas_water_meter/frontend/entrypoint.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [
    resolve(),
    terser({
      format: { comments: false },
    }),
  ],
};
