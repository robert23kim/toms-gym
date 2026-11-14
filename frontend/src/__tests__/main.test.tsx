const mockRender = jest.fn();
const mockCreateRoot = jest.fn(() => ({ render: mockRender }));
let release: () => void = () => {};
const mockRestore = jest.fn(() => new Promise<void>((r) => { release = r; }));
jest.mock("react-dom/client", () => ({ createRoot: mockCreateRoot }));
jest.mock("../App.tsx", () => ({ __esModule: true, default: () => null }));
jest.mock("../index.css", () => ({}));
jest.mock("../lib/telemetry", () => ({ initTelemetry: jest.fn() }));
jest.mock("../lib/staleChunk", () => ({ installStaleChunkReload: jest.fn() }));
jest.mock("../lib/identity", () => ({ restoreIdentity: mockRestore }));

test("the app renders only after the native identity restore settles", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  jest.isolateModules(() => {
    require("../main.tsx");
  });
  expect(mockRestore).toHaveBeenCalledTimes(1);
  await Promise.resolve();
  await Promise.resolve();
  expect(mockCreateRoot).not.toHaveBeenCalled();
  expect(mockRender).not.toHaveBeenCalled();
  release();
  await new Promise((r) => setTimeout(r, 0));
  expect(mockRender).toHaveBeenCalledTimes(1);
});
