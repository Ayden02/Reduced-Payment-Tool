import csv
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


TWOPLACES = Decimal("0.01")
HUNDRED = Decimal("100")


def parse_money(value: str) -> Decimal:
    """Convert user-entered currency text such as '$1,250.50' to Decimal."""
    cleaned = value.replace("$", "").replace(",", "").strip()
    amount = Decimal(cleaned)
    if not amount.is_finite():
        raise InvalidOperation
    return amount.quantize(TWOPLACES)


def money(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def allocate_cents(providers, reduced_total: Decimal):
    """
    Allocate the reduced total.

    Exempt providers receive their full original charge.
    The remaining pool is distributed among non-exempt providers in proportion
    to their original charges.

    Uses a largest-remainder cent allocation so displayed payments always sum
    exactly to the reduced total.
    """
    original_total = sum((p["original"] for p in providers), Decimal("0.00"))
    exempt_total = sum(
        (p["original"] for p in providers if p["exempt"]),
        Decimal("0.00"),
    )
    non_exempt = [p for p in providers if not p["exempt"]]
    non_exempt_original_total = sum(
        (p["original"] for p in non_exempt),
        Decimal("0.00"),
    )

    if original_total <= 0:
        raise ValueError("The original total must be greater than $0.00.")

    if reduced_total < 0:
        raise ValueError("The reduced total cannot be negative.")

    if reduced_total > original_total:
        raise ValueError(
            "The reduced total cannot be greater than the original total."
        )

    if reduced_total < exempt_total:
        raise ValueError(
            f"The reduced total ({money(reduced_total)}) is less than the "
            f"amount required for exempt providers ({money(exempt_total)})."
        )

    remaining_pool = reduced_total - exempt_total

    if not non_exempt:
        if remaining_pool != Decimal("0.00"):
            raise ValueError(
                "All providers are exempt, so the reduced total must equal "
                "the original total."
            )
        raw_allocations = {}
    else:
        if non_exempt_original_total <= 0 and remaining_pool > 0:
            raise ValueError(
                "The remaining amount cannot be allocated because all "
                "non-exempt provider charges are $0.00."
            )

        # Work in integer cents to guarantee that allocations add up exactly.
        pool_cents = int((remaining_pool * HUNDRED).to_integral_value())
        rows = []
        floor_sum = 0

        for index, p in enumerate(non_exempt):
            if non_exempt_original_total == 0:
                raw_cents = Decimal("0")
            else:
                raw_cents = (
                    Decimal(pool_cents)
                    * p["original"]
                    / non_exempt_original_total
                )

            floor_cents = int(raw_cents.to_integral_value(rounding=ROUND_DOWN))
            fraction = raw_cents - Decimal(floor_cents)
            floor_sum += floor_cents
            rows.append(
                {
                    "index": index,
                    "floor_cents": floor_cents,
                    "fraction": fraction,
                }
            )

        cents_left = pool_cents - floor_sum

        # Give leftover cents to the largest fractional remainders.
        for row in sorted(
            rows,
            key=lambda r: (-r["fraction"], r["index"]),
        )[:cents_left]:
            row["floor_cents"] += 1

        raw_allocations = {
            row["index"]: (Decimal(row["floor_cents"]) / HUNDRED).quantize(TWOPLACES)
            for row in rows
        }

    results = []
    non_exempt_index = 0

    for p in providers:
        overall_pct = (
            (p["original"] / original_total * HUNDRED)
            if original_total
            else Decimal("0")
        )

        if p["exempt"]:
            payment = p["original"]
            allocation_basis_pct = None
        else:
            allocation_basis_pct = (
                (p["original"] / non_exempt_original_total * HUNDRED)
                if non_exempt_original_total
                else Decimal("0")
            )
            payment = raw_allocations.get(non_exempt_index, Decimal("0.00"))
            non_exempt_index += 1

        results.append(
            {
                "name": p["name"],
                "original": p["original"],
                "overall_pct": overall_pct,
                "exempt": p["exempt"],
                "allocation_basis_pct": allocation_basis_pct,
                "payment": payment,
            }
        )

    return {
        "results": results,
        "original_total": original_total,
        "reduced_total": reduced_total,
        "exempt_total": exempt_total,
        "remaining_pool": remaining_pool,
    }


class ProviderPaymentAllocator(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Provider Payment Allocator")
        self.geometry("1040x700")
        self.minsize(900, 600)

        self.providers = []
        self.latest_calculation = None
        self.has_exempt_providers = False

        self._build_ui()
        self.after(150, self._ask_about_exempt_providers)

    def _build_ui(self):
        title = ttk.Label(
            self,
            text="Provider Payment Allocator",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(pady=(14, 4))

        subtitle = ttk.Label(
            self,
            text=(
                "Enter each provider's original charge, then enter the total "
                "amount available after reduction."
            ),
        )
        subtitle.pack(pady=(0, 10))

        input_frame = ttk.LabelFrame(self, text="Provider Entry", padding=10)
        input_frame.pack(fill="x", padx=14, pady=8)

        ttk.Label(input_frame, text="Provider name").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(
            input_frame, textvariable=self.name_var, width=32
        )
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(input_frame, text="Original charge").grid(
            row=0, column=2, sticky="w", padx=5, pady=5
        )
        self.original_var = tk.StringVar()
        self.original_entry = ttk.Entry(
            input_frame, textvariable=self.original_var, width=18
        )
        self.original_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        self.exempt_var = tk.BooleanVar(value=False)
        self.exempt_check = ttk.Checkbutton(
            input_frame,
            text="Exempt from reduction",
            variable=self.exempt_var,
        )
        self.exempt_check.grid(row=0, column=4, sticky="w", padx=8, pady=5)

        ttk.Button(
            input_frame, text="Add Provider", command=self.add_provider
        ).grid(row=0, column=5, padx=5, pady=5)

        input_frame.columnconfigure(1, weight=1)

        provider_frame = ttk.LabelFrame(self, text="Providers", padding=8)
        provider_frame.pack(fill="both", expand=True, padx=14, pady=8)

        columns = ("name", "original", "percent", "exempt")
        self.provider_tree = ttk.Treeview(
            provider_frame, columns=columns, show="headings", height=8
        )
        self.provider_tree.heading("name", text="Provider")
        self.provider_tree.heading("original", text="Original Charge")
        self.provider_tree.heading("percent", text="% of Original Total")
        self.provider_tree.heading("exempt", text="Exempt?")
        self.provider_tree.column("name", width=330)
        self.provider_tree.column("original", width=160, anchor="e")
        self.provider_tree.column("percent", width=160, anchor="e")
        self.provider_tree.column("exempt", width=90, anchor="center")
        self.provider_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            provider_frame, orient="vertical", command=self.provider_tree.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.provider_tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=14, pady=(0, 8))

        ttk.Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_selected,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_all,
        ).pack(side="left")

        calculation_frame = ttk.LabelFrame(
            self, text="Reduction", padding=10
        )
        calculation_frame.pack(fill="x", padx=14, pady=8)

        ttk.Label(
            calculation_frame,
            text="Total amount available after reduction",
        ).pack(side="left", padx=(0, 8))

        self.reduced_var = tk.StringVar()
        ttk.Entry(
            calculation_frame,
            textvariable=self.reduced_var,
            width=18,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            calculation_frame,
            text="Calculate Payments",
            command=self.calculate,
        ).pack(side="left")

        results_frame = ttk.LabelFrame(self, text="Payment Results", padding=8)
        results_frame.pack(fill="both", expand=True, padx=14, pady=8)

        result_columns = (
            "name",
            "original",
            "overall_pct",
            "exempt",
            "basis_pct",
            "payment",
        )
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=result_columns,
            show="headings",
            height=8,
        )

        headings = {
            "name": "Provider",
            "original": "Original",
            "overall_pct": "% of Original Total",
            "exempt": "Exempt?",
            "basis_pct": "Share of Remaining Providers",
            "payment": "Final Payment",
        }

        for column, heading in headings.items():
            self.results_tree.heading(column, text=heading)

        self.results_tree.column("name", width=260)
        self.results_tree.column("original", width=120, anchor="e")
        self.results_tree.column("overall_pct", width=145, anchor="e")
        self.results_tree.column("exempt", width=75, anchor="center")
        self.results_tree.column("basis_pct", width=185, anchor="e")
        self.results_tree.column("payment", width=130, anchor="e")
        self.results_tree.pack(side="left", fill="both", expand=True)

        results_scrollbar = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.results_tree.yview,
        )
        results_scrollbar.pack(side="right", fill="y")
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)

        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=14, pady=(0, 14))

        self.summary_var = tk.StringVar(value="No calculation yet.")
        ttk.Label(footer, textvariable=self.summary_var).pack(side="left")

        ttk.Button(
            footer,
            text="Export CSV",
            command=self.export_csv,
        ).pack(side="right")

        self.bind("<Return>", lambda _event: self.add_provider())

    def _ask_about_exempt_providers(self):
        self.has_exempt_providers = messagebox.askyesno(
            "Exempt Providers",
            "Are any providers exempt from the reduction and required to "
            "receive their full original amount?",
            parent=self,
        )

        if self.has_exempt_providers:
            self.exempt_check.state(["!disabled"])
        else:
            self.exempt_var.set(False)
            self.exempt_check.state(["disabled"])

        self.name_entry.focus_set()

    def _refresh_provider_table(self):
        for item in self.provider_tree.get_children():
            self.provider_tree.delete(item)

        total = sum(
            (p["original"] for p in self.providers),
            Decimal("0.00"),
        )

        for index, p in enumerate(self.providers):
            pct = (
                p["original"] / total * HUNDRED
                if total
                else Decimal("0")
            )
            self.provider_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    p["name"],
                    money(p["original"]),
                    f"{pct:.2f}%",
                    "Yes" if p["exempt"] else "No",
                ),
            )

    def _clear_results(self):
        self.latest_calculation = None
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.summary_var.set("No calculation yet.")

    def add_provider(self):
        name = self.name_var.get().strip()

        if not name:
            messagebox.showerror(
                "Missing Provider",
                "Please enter a provider name.",
                parent=self,
            )
            return

        try:
            original = parse_money(self.original_var.get())
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                "Invalid Charge",
                "Enter a valid dollar amount, such as 1250 or 1250.50.",
                parent=self,
            )
            return

        if original < 0:
            messagebox.showerror(
                "Invalid Charge",
                "The original charge cannot be negative.",
                parent=self,
            )
            return

        exempt = (
            bool(self.exempt_var.get())
            if self.has_exempt_providers
            else False
        )

        self.providers.append(
            {
                "name": name,
                "original": original,
                "exempt": exempt,
            }
        )

        self.name_var.set("")
        self.original_var.set("")
        self.exempt_var.set(False)
        self._refresh_provider_table()
        self._clear_results()
        self.name_entry.focus_set()

    def remove_selected(self):
        selected = self.provider_tree.selection()
        if not selected:
            return

        indices = sorted((int(item) for item in selected), reverse=True)

        for index in indices:
            if 0 <= index < len(self.providers):
                self.providers.pop(index)

        self._refresh_provider_table()
        self._clear_results()

    def clear_all(self):
        if not self.providers:
            return

        if not messagebox.askyesno(
            "Clear All",
            "Remove all providers and start over?",
            parent=self,
        ):
            return

        self.providers.clear()
        self.reduced_var.set("")
        self._refresh_provider_table()
        self._clear_results()
        self._ask_about_exempt_providers()

    def calculate(self):
        if not self.providers:
            messagebox.showerror(
                "No Providers",
                "Add at least one provider before calculating.",
                parent=self,
            )
            return

        try:
            reduced_total = parse_money(self.reduced_var.get())
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                "Invalid Reduced Total",
                "Enter a valid reduced total, such as 10000 or 10000.00.",
                parent=self,
            )
            return

        try:
            calculation = allocate_cents(self.providers, reduced_total)
        except ValueError as error:
            messagebox.showerror(
                "Cannot Calculate",
                str(error),
                parent=self,
            )
            return

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for row in calculation["results"]:
            basis = (
                "Full amount"
                if row["exempt"]
                else f"{row['allocation_basis_pct']:.2f}%"
            )

            self.results_tree.insert(
                "",
                "end",
                values=(
                    row["name"],
                    money(row["original"]),
                    f"{row['overall_pct']:.2f}%",
                    "Yes" if row["exempt"] else "No",
                    basis,
                    money(row["payment"]),
                ),
            )

        self.latest_calculation = calculation
        self.summary_var.set(
            f"Original total: {money(calculation['original_total'])}   |   "
            f"Reduced total: {money(calculation['reduced_total'])}   |   "
            f"Exempt providers: {money(calculation['exempt_total'])}   |   "
            f"Remaining pool: {money(calculation['remaining_pool'])}"
        )

    def export_csv(self):
        if not self.latest_calculation:
            messagebox.showinfo(
                "Nothing to Export",
                "Run a calculation first.",
                parent=self,
            )
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Provider Payment Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="provider_payment_results.csv",
        )

        if not path:
            return

        calculation = self.latest_calculation

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "Provider",
                    "Original Charge",
                    "Percent of Original Total",
                    "Exempt",
                    "Share of Remaining Providers",
                    "Final Payment",
                ]
            )

            for row in calculation["results"]:
                writer.writerow(
                    [
                        row["name"],
                        f"{row['original']:.2f}",
                        f"{row['overall_pct']:.2f}%",
                        "Yes" if row["exempt"] else "No",
                        (
                            "Full amount"
                            if row["exempt"]
                            else f"{row['allocation_basis_pct']:.2f}%"
                        ),
                        f"{row['payment']:.2f}",
                    ]
                )

            writer.writerow([])
            writer.writerow(["Original Total", f"{calculation['original_total']:.2f}"])
            writer.writerow(["Reduced Total", f"{calculation['reduced_total']:.2f}"])
            writer.writerow(["Exempt Total", f"{calculation['exempt_total']:.2f}"])
            writer.writerow(["Remaining Pool", f"{calculation['remaining_pool']:.2f}"])

        messagebox.showinfo(
            "Export Complete",
            "The CSV file was saved successfully.",
            parent=self,
        )


if __name__ == "__main__":
    app = ProviderPaymentAllocator()
    app.mainloop()
