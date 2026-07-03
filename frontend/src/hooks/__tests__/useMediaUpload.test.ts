import { renderHook, act } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { useMediaUpload } from "../useMediaUpload";

beforeAll(() => {
  global.URL.createObjectURL = jest.fn(() => "blob:preview");
  global.URL.revokeObjectURL = jest.fn();
});

function changeEventWith(file: File) {
  return { target: { files: [file] } } as unknown as ChangeEvent<HTMLInputElement>;
}

describe("useMediaUpload", () => {
  it("accepts a valid file and builds a preview", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 1024 })
    );
    const file = new File(["x"], "card.jpg", { type: "image/jpeg" });
    act(() => result.current.onInputChange(changeEventWith(file)));
    expect(result.current.file).toBe(file);
    expect(result.current.previewUrl).toBe("blob:preview");
    expect(result.current.error).toBeNull();
  });

  it("rejects the wrong media type", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 1024 })
    );
    const file = new File(["x"], "clip.mp4", { type: "video/mp4" });
    act(() => result.current.onInputChange(changeEventWith(file)));
    expect(result.current.file).toBeNull();
    expect(result.current.error).toBe("Please choose an image file");
  });

  it("rejects oversized files with a MB message", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 20 * 1024 * 1024 })
    );
    const big = new File([new ArrayBuffer(21 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });
    act(() => result.current.onInputChange(changeEventWith(big)));
    expect(result.current.file).toBeNull();
    expect(result.current.error).toBe("Image must be under 20MB");
  });
});
