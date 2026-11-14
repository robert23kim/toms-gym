import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import BowlingChallenge from "../BowlingChallenge";
import FindProfilePage from "../FindProfilePage";
import FindProfile from "../../components/FindProfile";
import SignIn from "../SignIn";
import FileTicket from "../FileTicket";
import GolfUpload from "../GolfUpload";
import BowlingUpload from "../BowlingUpload";
import BowlingSheetUpload from "../BowlingSheetUpload";
import { RegistrationForm } from "../../components/RegistrationForm";
import CreateProfile from "../../components/CreateProfile";
import { PasswordResetForm } from "../../components/PasswordResetForm";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../components/FairwayScope", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../components/GhibliAvatar", () => ({ __esModule: true, default: () => <div /> }));
jest.mock("axios");
jest.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ handleLoginSuccess: jest.fn() }) }));

const REMEMBERED = "sam@example.com";

const storage = (values: Record<string, string>) =>
  (localStorage.getItem as jest.Mock).mockImplementation((k: string) => values[k] ?? null);

const forms: [string, React.ReactElement][] = [
  ["Find Profile page", <FindProfilePage />],
  ["Find Profile dialog", <FindProfile onClose={() => {}} />],
  ["Sign in", <SignIn />],
  ["Feedback", <FileTicket />],
  ["Golf upload", <GolfUpload />],
  ["Bowling upload", <BowlingUpload />],
  ["Bowling sheet upload", <BowlingSheetUpload />],
  ["Registration", <RegistrationForm />],
  ["Create profile", <CreateProfile onClose={() => {}} onSubmit={async () => true} />],
  ["Password reset request", <PasswordResetForm />],
];

const emailInput = (container: HTMLElement) =>
  container.querySelector('input[type="email"]') as HTMLInputElement | null;

describe("email pre-fill from the remembered identity", () => {
  afterEach(() => (localStorage.getItem as jest.Mock).mockReset());

  test.each(forms)("%s pre-fills the remembered email and keeps it editable", (_name, ui) => {
    storage({ userEmail: REMEMBERED });
    const { container } = render(<MemoryRouter>{ui}</MemoryRouter>);
    const input = emailInput(container);
    expect(input).not.toBeNull();
    expect(input!.value).toBe(REMEMBERED);
    expect(input).not.toHaveAttribute("readonly");
    expect(input).not.toBeDisabled();
  });

  test.each(forms)("%s stays empty on a first run", (_name, ui) => {
    storage({});
    const { container } = render(<MemoryRouter>{ui}</MemoryRouter>);
    expect(emailInput(container)!.value).toBe("");
  });

  test("an id stored where the email belongs never pre-fills", () => {
    storage({ userEmail: "u-1" });
    render(
      <MemoryRouter>
        <SignIn />
      </MemoryRouter>,
    );
    expect(screen.getByRole("textbox")).toHaveValue("");
  });
});

describe("BowlingChallenge upload email", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = jest.fn();
  });
  afterEach(() => (localStorage.getItem as jest.Mock).mockReset());

  test.each([
    ["pre-fills the remembered email", { userEmail: REMEMBERED }, REMEMBERED],
    ["stays empty on a first run", {}, ""],
  ])("%s", async (_name, values, want) => {
    storage(values);
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        competition: { id: "c1", name: "Bowl", lifttypes: ["Bowling"], start_date: "2026-01-01", end_date: "2099-01-01" },
        results: [],
        participants: [],
      },
    });
    const { container } = render(
      <MemoryRouter initialEntries={["/bowling/c1"]}>
        <Routes>
          <Route path="/bowling/:id" element={<BowlingChallenge />} />
        </Routes>
      </MemoryRouter>,
    );
    await new Promise((r) => setTimeout(r, 80));
    for (const b of Array.from(container.querySelectorAll("button"))) if (/upload/i.test(b.textContent || "")) b.click();
    await waitFor(() => expect(emailInput(container)).not.toBeNull());
    expect(emailInput(container)!.value).toBe(want);
  });
});
