import { BowlingSheetType } from "./api";

export interface SheetFormOptions {
  sheetType: BowlingSheetType;
  playedOn: string;
  userId?: string | null;
  email?: string;
}

export const buildSheetForm = (file: File, opts: SheetFormOptions): FormData => {
  const form = new FormData();
  form.append("image", file);
  form.append("sheet_type", opts.sheetType);
  form.append("played_on", opts.playedOn);
  if (opts.userId) form.append("user_id", opts.userId);
  else if (opts.email) form.append("email", opts.email);
  return form;
};
