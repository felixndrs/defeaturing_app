import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLangStore } from "../i18n";
import { ConfirmNewProject } from "./ConfirmNewProject";

function renderDialog(overrides: Partial<Parameters<typeof ConfirmNewProject>[0]> = {}) {
  const onCancel = vi.fn();
  const onConfirm = vi.fn();
  render(
    <ConfirmNewProject
      runId="run-42"
      projectName="Halterung"
      undecided={0}
      total={4}
      onCancel={onCancel}
      onConfirm={onConfirm}
      {...overrides}
    />,
  );
  return { onCancel, onConfirm };
}

describe("ConfirmNewProject", () => {
  beforeEach(() => {
    useLangStore.getState().setLang("de");
  });

  it("hands over the deep link that reopens this review", () => {
    // The whole point of the dialog: ?run=... is the only way back, and the
    // review screen shows it nowhere else.
    renderDialog();
    const input = screen.getByDisplayValue(/run=run-42/) as HTMLInputElement;
    expect(input.value).toContain(window.location.origin);
    expect(input.readOnly).toBe(true);
  });

  it("copies the link to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    renderDialog();
    fireEvent.click(screen.getByText("Link kopieren"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("?run=run-42"));
    expect(await screen.findByText("Kopiert")).toBeTruthy();
  });

  it("survives a denied clipboard", async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    const { onConfirm } = renderDialog();
    fireEvent.click(screen.getByText("Link kopieren"));
    // No unhandled rejection, dialog still usable.
    expect(screen.getByText("Neues Projekt")).toBeTruthy();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("warns about undecided changes, and only then", () => {
    renderDialog({ undecided: 3, total: 4 });
    expect(screen.getByText("3 von 4 Änderungen sind noch nicht entschieden.")).toBeTruthy();
  });

  it("stays quiet when everything is decided", () => {
    renderDialog({ undecided: 0, total: 4 });
    expect(screen.queryByText(/noch nicht entschieden/)).toBeNull();
  });

  it("offers the report downloads before leaving", () => {
    renderDialog();
    expect(screen.getByText("PDF")).toBeTruthy();
    expect(screen.getByText("HTML-Paket")).toBeTruthy();
  });

  it("confirms only on the confirm button", () => {
    const { onConfirm, onCancel } = renderDialog();
    fireEvent.click(screen.getByText("Neues Projekt"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("cancels on the button, on Escape and on the backdrop", () => {
    const { onCancel } = renderDialog();
    fireEvent.click(screen.getByText("Abbrechen"));
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.click(document.querySelector(".fixed.inset-0")!);
    expect(onCancel).toHaveBeenCalledTimes(3);
  });

  it("does not cancel when the dialog body itself is clicked", () => {
    const { onCancel } = renderDialog();
    fireEvent.click(screen.getByText("Neues Projekt starten?"));
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("follows the language switch", () => {
    useLangStore.getState().setLang("en");
    renderDialog();
    expect(screen.getByText("Start a new project?")).toBeTruthy();
    expect(screen.getByText("Copy link")).toBeTruthy();
  });
});
