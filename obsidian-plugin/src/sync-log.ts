import { type App, Modal } from "obsidian";

const MAX_LINES = 10000;

export class SyncLog {
    private lines: string[] = [];

    log(folder: string, message: string): void {
        const now = new Date();
        const timestamp = now.toISOString().slice(0, 19).replace("T", " ");
        const entry = `[${timestamp} ${folder}] ${message}`;
        this.lines.push(entry);
        if (this.lines.length > MAX_LINES) {
            this.lines = this.lines.slice(-MAX_LINES);
        }
    }

    getLines(): string[] {
        return this.lines;
    }

    clear(): void {
        this.lines = [];
    }
}

export interface SyncLogModalOptions {
    folders: string[];
    onSync: (folder: string) => void;
}

export class SyncLogModal extends Modal {
    private syncLog: SyncLog;
    private options?: SyncLogModalOptions;
    private intervalId: number | null = null;
    private pre: HTMLPreElement | null = null;
    private lastLineCount = 0;

    constructor(app: App, syncLog: SyncLog, options?: SyncLogModalOptions) {
        super(app);
        this.syncLog = syncLog;
        this.options = options;
    }

    onOpen(): void {
        const { contentEl, modalEl } = this;
        contentEl.addClass("sync-log-modal");

        modalEl.style.width = "80vw";
        modalEl.style.maxWidth = "900px";
        contentEl.style.height = "80vh";
        contentEl.style.display = "flex";
        contentEl.style.flexDirection = "column";

        const headerContainer = contentEl.createDiv();
        headerContainer.style.display = "flex";
        headerContainer.style.justifyContent = "space-between";
        headerContainer.style.alignItems = "center";
        headerContainer.style.marginBottom = "16px";

        if (this.options && this.options.folders.length > 0) {
            const select = headerContainer.createEl("select");
            select.createEl("option", { text: "Sync now…", value: "" });
            for (const folder of this.options.folders) {
                select.createEl("option", { text: folder, value: folder });
            }
            select.addEventListener("change", () => {
                if (select.value) {
                    this.options?.onSync(select.value);
                    select.value = "";
                }
            });
        }

        const clearButton = headerContainer.createEl("button", { text: "Clear" });
        clearButton.addEventListener("click", () => {
            this.syncLog.clear();
            this.lastLineCount = 0;
            this.render();
        });

        this.pre = contentEl.createEl("pre");
        this.pre.style.flex = "1";
        this.pre.style.overflow = "auto";
        this.pre.style.fontFamily = "monospace";
        this.pre.style.fontSize = "12px";
        this.pre.style.whiteSpace = "pre-wrap";
        this.pre.style.margin = "0";
        this.pre.style.userSelect = "text";

        this.render();
        this.intervalId = window.setInterval(() => this.render(), 500);
    }

    onClose(): void {
        if (this.intervalId !== null) {
            window.clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.contentEl.empty();
    }

    private render(): void {
        if (!this.pre) {
            return;
        }

        const lines = this.syncLog.getLines();
        if (lines.length === 0) {
            this.pre.setText("No sync activity yet.");
            return;
        }

        if (lines.length === this.lastLineCount) {
            return;
        }
        this.lastLineCount = lines.length;

        const wasAtBottom =
            this.pre.scrollTop >= this.pre.scrollHeight - this.pre.clientHeight - 10;

        this.pre.setText(lines.join("\n"));

        if (wasAtBottom) {
            this.pre.scrollTop = this.pre.scrollHeight;
        }
    }
}
