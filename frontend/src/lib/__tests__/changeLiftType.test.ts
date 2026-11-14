import axios from "axios";
import { changeLiftType } from "../api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("axios");

const mockedAxios = axios as jest.Mocked<typeof axios>;

it("posts the owner's pick to the attempt's lift-type endpoint", async () => {
  mockedAxios.post.mockResolvedValue({ data: { attempt_id: "a-1", lift_type: "Situp", status: "queued" } });
  const res = await changeLiftType("a-1", "Situp", "u-1");
  expect(mockedAxios.post).toHaveBeenCalledWith("https://test-api.example/attempts/a-1/lift-type", {
    lift_type: "Situp",
    user_id: "u-1",
  });
  expect(res).toEqual({ attempt_id: "a-1", lift_type: "Situp", status: "queued" });
});
