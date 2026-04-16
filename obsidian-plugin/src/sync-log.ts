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
}

export class SyncLogModal extends Modal {
    private syncLog: SyncLog;
    private intervalId: number | null = null;
    private pre: HTMLPreElement | null = null;

    constructor(app: App, syncLog: SyncLog) {
        super(app);
        this.syncLog = syncLog;
    }

    onOpen(): void {
        const { contentEl } = this;
        contentEl.addClass("sync-log-modal");

        contentEl.style.height = "80vh";
        contentEl.style.display = "flex";
        contentEl.style.flexDirection = "column";

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

        const wasAtBottom =
            this.pre.scrollTop >= this.pre.scrollHeight - this.pre.clientHeight - 10;

        this.pre.setText(lines.join("\n"));

        if (wasAtBottom) {
            this.pre.scrollTop = this.pre.scrollHeight;
        }
    }
}
