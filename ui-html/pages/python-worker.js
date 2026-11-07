import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

let pyodide;

const ready = loadPyodide({
  indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/"
}).then(runtime => {
  pyodide = runtime;
  self.postMessage({ type: "ready" });
});

self.onmessage = async event => {
  if (event.data.type !== "run") return;

  try {
    await ready;

    let output = "";

    pyodide.setStdout({
      batched: text => {
        output += text + "\n";
      }
    });

    pyodide.setStderr({
      batched: text => {
        output += text + "\n";
      }
    });

    const result = await pyodide.runPythonAsync(
      event.data.code
    );

    if (result !== undefined) {
      output += String(result);
    }

    self.postMessage({
      type: "result",
      output
    });

  } catch (error) {
    self.postMessage({
      type: "error",
      message: String(error)
    });
  }
};
