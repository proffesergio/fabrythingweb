import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CopyMenuDialog from "./CopyMenuDialog";

jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockCallApi = jest.fn();
jest.mock("../../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

const restaurants = [{ id: 1, name: "Source" }, { id: 2, name: "Target" }];
const preview = {
    categories_created: 2, categories_merged: 1,
    items_copied: 12, items_skipped: 3, options_copied: 4,
};

beforeEach(() => {
    mockCallApi.mockImplementation(({ params }) => Promise.resolve({
        status: 200,
        data: { data: preview, message: params?.dry_run ? "Copy preview" : "Menu copied" },
    }));
});
afterEach(() => jest.clearAllMocks());

const pickSource = async () => {
    fireEvent.mouseDown(screen.getByLabelText(/copy menu from/i));
    fireEvent.click(await screen.findByRole("option", { name: "Source" }));
};

describe("CopyMenuDialog", () => {
    it("previews the copy before writing anything", async () => {
        render(<CopyMenuDialog open restaurants={restaurants} targetRestaurant={2}
            selectedItemIds={[]} onClose={jest.fn()} onCopied={jest.fn()} />);
        await pickSource();

        await waitFor(() => expect(screen.getByText(/12 items will be copied/i)).toBeInTheDocument());
        expect(screen.getByText(/3 skipped/i)).toBeInTheDocument();
        expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({
            url: "food/admin/menu/copy/", params: { dry_run: "true" },
        }));
    });

    it("performs the copy and reports the result", async () => {
        const onCopied = jest.fn();
        render(<CopyMenuDialog open restaurants={restaurants} targetRestaurant={2}
            selectedItemIds={[]} onClose={jest.fn()} onCopied={onCopied} />);
        await pickSource();
        await screen.findByText(/12 items will be copied/i);

        fireEvent.click(screen.getByRole("button", { name: /copy menu/i }));
        await waitFor(() => expect(onCopied).toHaveBeenCalled());
    });
});
