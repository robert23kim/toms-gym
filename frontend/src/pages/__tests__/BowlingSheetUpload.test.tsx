import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import BowlingSheetUpload from "../BowlingSheetUpload";
import { uploadBowlingSheet } from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("../../lib/api", () => ({ uploadBowlingSheet: jest.fn() }));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const mockedUpload = uploadBowlingSheet as jest.MockedFunction<typeof uploadBowlingSheet>;

// jsdom implements neither object-URL function; the preview <img> needs both.
Object.defineProperty(URL, "createObjectURL", { value: jest.fn(() => "blob:preview"), writable: true });
Object.defineProperty(URL, "revokeObjectURL", { value: jest.fn(), writable: true });

// jest.setup.js installs a no-op localStorage (getItem always returns
// undefined); swap in a working store, as MagicLink.test does.
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

const renderPage = (props: { autoCamera?: boolean } = {}) =>
  render(
    <MemoryRouter>
      <BowlingSheetUpload {...props} />
    </MemoryRouter>,
  );

const pickFile = () => {
  const input = document.getElementById("bowling-sheet-upload") as HTMLInputElement;
  const file = new File(["sheet"], "night.jpg", { type: "image/jpeg" });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
};

const postedForm = (): FormData => mockedUpload.mock.calls[0][0];

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("userId", "user-1");
  mockedUpload.mockResolvedValue({
    sheet_id: "sheet-9",
    sheet_type: "night",
    played_on: "2026-08-28",
    image_url: null,
    team_name: null,
    processing_status: "parsed",
    players: [],
    flagged_count: 0,
  });
});

afterEach(() => localStorage.clear());

describe("BowlingSheetUpload", () => {
  it("renders a library input and a camera input with capture=environment", () => {
    renderPage();
    const camera = document.getElementById("bowling-sheet-camera");
    const library = document.getElementById("bowling-sheet-upload");
    expect(camera).not.toBeNull();
    expect(camera!.getAttribute("capture")).toBe("environment");
    expect(camera!.getAttribute("accept")).toBe("image/*");
    expect(library).not.toBeNull();
    expect(library!.hasAttribute("capture")).toBe(false);
  });

  it("auto-clicks the camera input when autoCamera is set", () => {
    const clickSpy = jest
      .spyOn(HTMLInputElement.prototype, "click")
      .mockImplementation(() => {});
    renderPage({ autoCamera: true });
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  it("posts sheet_type=night by default and navigates to the review page", async () => {
    renderPage();
    pickFile();
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));

    await waitFor(() => expect(mockedUpload).toHaveBeenCalled());
    const form = postedForm();
    expect(form.get("sheet_type")).toBe("night");
    expect(form.get("user_id")).toBe("user-1");
    expect(form.get("played_on")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(mockNavigate).toHaveBeenCalledWith("/bowling/scoresheet/sheet-9");
  });

  it("posts sheet_type=game when the single-game toggle is picked", async () => {
    renderPage();
    pickFile();
    fireEvent.click(screen.getByRole("radio", { name: /single game/i }));
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));

    await waitFor(() => expect(mockedUpload).toHaveBeenCalled());
    expect(postedForm().get("sheet_type")).toBe("game");
  });

  it("sends the edited date", async () => {
    renderPage();
    pickFile();
    fireEvent.change(screen.getByLabelText(/date bowled/i), {
      target: { value: "2026-08-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));

    await waitFor(() => expect(mockedUpload).toHaveBeenCalled());
    expect(postedForm().get("played_on")).toBe("2026-08-01");
  });

  it("asks for an email when no user is stored and posts it instead of user_id", async () => {
    localStorage.clear();
    renderPage();
    pickFile();
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));
    expect(await screen.findByText(/enter your email/i)).toBeInTheDocument();
    expect(mockedUpload).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText(/^email$/i), {
      target: { value: "tom@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));
    await waitFor(() => expect(mockedUpload).toHaveBeenCalled());
    const form = postedForm();
    expect(form.get("email")).toBe("tom@example.com");
    expect(form.get("user_id")).toBeNull();
  });

  it("surfaces an upload failure without navigating", async () => {
    mockedUpload.mockRejectedValue(new Error("boom"));
    renderPage();
    pickFile();
    fireEvent.click(screen.getByRole("button", { name: /read score sheet/i }));
    expect(await screen.findByText(/upload failed/i)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
