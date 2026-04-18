import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import TeePickerDrawer from "../TeePickerDrawer";
import type { GolfTee, GolfCourse } from "../../../lib/types";

const baseCourse: GolfCourse = {
  id: "c1",
  name: "Pebble Beach",
  city: "Pebble Beach",
  state: "CA",
  country: "USA",
  latitude: 36.5,
  longitude: -121.9,
  holes: 18,
  status: "verified",
};

const makeTee = (overrides: Partial<GolfTee> = {}): GolfTee => ({
  id: "t1",
  name: "Blue",
  color_hex: "#2563eb",
  rating_18: 71.3,
  slope_18: 130,
  rating_9_front: null,
  slope_9_front: null,
  rating_9_back: null,
  slope_9_back: null,
  yardage: 6700,
  par: 72,
  hole_pars: null,
  hole_yardages: null,
  hole_handicaps: null,
  ...overrides,
});

const wrap = (node: React.ReactNode) => node;

describe("TeePickerDrawer", () => {
  test("renders nothing when closed", () => {
    const { container } = render(
      wrap(
        <TeePickerDrawer
          open={false}
          course={baseCourse}
          tees={[makeTee()]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    expect(container.querySelector('[data-testid="tee-picker-drawer"]')).toBeNull();
  });

  test("renders up to 4 tee cards when open", () => {
    const tees: GolfTee[] = [
      makeTee({ id: "t1", name: "Black",  slope_18: 140, rating_18: 74.0 }),
      makeTee({ id: "t2", name: "Blue",   slope_18: 132, rating_18: 72.1 }),
      makeTee({ id: "t3", name: "White",  slope_18: 125, rating_18: 70.6 }),
      makeTee({ id: "t4", name: "Gold",   slope_18: 118, rating_18: 68.9 }),
      makeTee({ id: "t5", name: "Red",    slope_18: 110, rating_18: 66.8 }),
    ];
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={tees}
          selectedTeeId="t2"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    const cards = screen.getAllByTestId(/^tee-card-/);
    expect(cards).toHaveLength(4);
  });

  test("selected tee card gets the fw-selected class", () => {
    const tees: GolfTee[] = [
      makeTee({ id: "t1", name: "Black", slope_18: 140, rating_18: 74.0 }),
      makeTee({ id: "t2", name: "Blue",  slope_18: 130, rating_18: 72.0 }),
    ];
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={tees}
          selectedTeeId="t2"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    expect(screen.getByTestId("tee-card-t2").className).toMatch(/fw-selected/);
    expect(screen.getByTestId("tee-card-t1").className).not.toMatch(/fw-selected/);
  });

  test("live differential preview reflects rating/slope/score", () => {
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee({ id: "t1", slope_18: 128, rating_18: 71.2 })]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    // ((80 - 71.2) * 113) / 128 = 7.76875 → "7.8"
    expect(screen.getByTestId("tee-picker-differential")).toHaveTextContent("7.8");
  });

  test("editing slope recomputes the live differential", () => {
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee({ id: "t1", slope_18: 128, rating_18: 71.2 })]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    const slopeInput = screen.getByLabelText(/slope/i) as HTMLInputElement;
    fireEvent.change(slopeInput, { target: { value: "113" } });
    // ((80 - 71.2) * 113) / 113 = 8.8
    expect(screen.getByTestId("tee-picker-differential")).toHaveTextContent("8.8");
  });

  test("editing rating recomputes the live differential", () => {
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee({ id: "t1", slope_18: 113, rating_18: 72.0 })]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    const ratingInput = screen.getByLabelText(/rating/i) as HTMLInputElement;
    fireEvent.change(ratingInput, { target: { value: "70.0" } });
    // ((80 - 70.0) * 113) / 113 = 10.0
    expect(screen.getByTestId("tee-picker-differential")).toHaveTextContent("10.0");
  });

  test("selecting a different tee card invokes the tee's rating/slope", () => {
    const tees = [
      makeTee({ id: "t1", name: "Black", slope_18: 140, rating_18: 74.0 }),
      makeTee({ id: "t2", name: "Blue",  slope_18: 120, rating_18: 70.0 }),
    ];
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={tees}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
        />,
      ),
    );
    fireEvent.click(screen.getByTestId("tee-card-t2"));
    // ((80 - 70.0) * 113) / 120 = 9.416... → "9.4"
    expect(screen.getByTestId("tee-picker-differential")).toHaveTextContent("9.4");
    expect(screen.getByTestId("tee-card-t2").className).toMatch(/fw-selected/);
  });

  test("apply fires onApply with selected tee_id and current overrides", () => {
    const handleApply = jest.fn();
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee({ id: "t1", slope_18: 128, rating_18: 71.2, yardage: 6700 })]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={handleApply}
          onClose={() => {}}
        />,
      ),
    );
    fireEvent.change(screen.getByLabelText(/slope/i), { target: { value: "125" } });
    fireEvent.change(screen.getByLabelText(/yardage/i), { target: { value: "6600" } });
    fireEvent.click(screen.getByRole("button", { name: /apply/i }));

    expect(handleApply).toHaveBeenCalledTimes(1);
    const args = handleApply.mock.calls[0][0];
    expect(args.tee_id).toBe("t1");
    expect(args.rating_18).toBe(71.2);
    expect(args.slope_18).toBe(125);
    expect(args.yardage).toBe(6600);
  });

  test("close button fires onClose", () => {
    const handleClose = jest.fn();
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee()]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={handleClose}
        />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  test("look-up button invokes onLookup with course name + near", async () => {
    const handleLookup = jest.fn(async () => []);
    render(
      wrap(
        <TeePickerDrawer
          open
          course={baseCourse}
          tees={[makeTee()]}
          selectedTeeId="t1"
          adjustedGrossScore={80}
          onApply={() => {}}
          onClose={() => {}}
          onLookup={handleLookup}
        />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /look up official/i }));
    await waitFor(() => expect(handleLookup).toHaveBeenCalledTimes(1));
    expect(handleLookup).toHaveBeenCalledWith(baseCourse.name, [
      baseCourse.latitude,
      baseCourse.longitude,
    ]);
  });
});
